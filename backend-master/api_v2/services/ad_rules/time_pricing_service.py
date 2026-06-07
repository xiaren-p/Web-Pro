"""分时策略执行器（time_pricing_service）。

两个阶段合并为一个服务：
  - 分时开始：awaiting_start=YES + 当前在时段内 → 写 START + is_time_pricing=YES + awaiting_start=NO + rule_updated_today=False
  - 分时回调：awaiting_start=NO + 当前不在时段内 → 写 CALLBACK + is_time_pricing=NO + awaiting_start=YES + rule_updated_today=False

  - 兜底重置：awaiting_start=YES + 不在时段内 + rule_updated_today=True → 仅 reset rule_updated_today（防止永久卡死 #1）

时段判断：
  直接使用 AdTimePricingHit 的 time_start_cn / time_end_cn 字段（北京时间 aware datetime，固定偏移 +8），
  与当前北京时间比对，无需重复解析策略 time_settings。
  上游 ad_time_pricing_service 在写入命中记录时已根据规则时段 + 站点 UTC 偏移算好四个时间值。
  多时段时取所有时段的最小 start 和最大 end 合并为一个覆盖窗口。

完整执行链路：
  ① 预加载策略 + 投放项（投放项按 campaign_keys 分批 Q 对象 SQL 查询）
  ② _process_single_hit()：从内存 item_map 取投放项 → 用 hit.time_start_cn / time_end_cn 判断时段 → 分流
  ③ _do_start / _do_callback：纯内存计算竞价 → 收集 SpBidAdjustment + AdTimePricingHit 待写列表
  ④ write_batch()：事务保护 → 先 bulk_create(SpBidAdjustment) → 再 bulk_update(AdTimePricingHit 状态)（#3）

处理流程：
  ├─ awaiting_start=YES + 在时段内 → _do_start()
  │   ├─ 取原始竞价(bid_before=当前实时竞价)
  │   ├─ 规则链式计算 bid_after
  │   ├─ append_start_adjustment()
  │   │   ├─ bid_before==bid_after → 标 SUCCESS，msg="竞价相等无需调整"
  │   │   └─ 不等 → 标 PENDING，待 bid_adjustment 调 API
  │   └─ UPDATE hit: is_time_pricing=YES, awaiting_start=NO, rule_updated_today=False
  │
  ├─ awaiting_start=NO + 不在时段内 → _do_callback()
  │   ├─ callback.type=none → 只改状态
  │   ├─ 检查是否有成功执行的 START 记录（#7：替代反推估算）
  │   ├─ 每条 item 计算回调竞价
  │   ├─ append_callback_adjustment()
  │   │   ├─ 回调竞价==数据库竞价 → 跳过不写
  │   │   └─ 不等 → 写 PENDING CALLBACK 记录
  │   └─ UPDATE hit: awaiting_start=YES, is_time_pricing=NO, rule_updated_today=False
  │
  └─ awaiting_start=YES + 不在时段内 + rule_updated_today=True → 兜底重置
      └─ UPDATE hit: rule_updated_today=False（防止永久卡死 #1）
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.models.sp_bid_adjustment import SpBidAdjustment
from api_v2.services.ad_rules.time_pricing_calculator import (
    MAX_ERROR_COUNT,
    build_item_map,
    calc_new_bid,
    get_ad_items,
    write_batch,
)
from api_v2.services.ad_rules.time_pricing_shared import (
    get_rules_for_segments,
)

logger = logging.getLogger(__name__)

# 北京时区常量
CN_TZ = dt_timezone(timedelta(hours=8))


# ============================================================
# 时段判断
# ============================================================

def _in_time_range(hit: AdTimePricingHit) -> bool:
    """判断当前北京时间是否在命中记录的时段内。

    用 ad_time_pricing_hit 表已计算好的 time_start_cn / time_end_cn（北京时间 aware datetime），
    与当前北京时间 datetime.now(固定偏移 +8) 比对。

    Args:
        hit: 分时命中记录（含 time_start_cn / time_end_cn）

    Returns:
        True 表示当前在时段内
    """
    if hit.time_start_cn is None or hit.time_end_cn is None:
        return False
    cn_tz = dt_timezone(timedelta(hours=8))
    now_cn = datetime.now(cn_tz)
    return hit.time_start_cn <= now_cn <= hit.time_end_cn


def _get_active_rules(strategy: LxTimePricingStrategy) -> list[dict]:
    """从策略 time_settings 中提取今天适用的规则（按 dayOfWeek 过滤）。

    统一使用 time_pricing_shared.get_rules_for_segments（#6 #13），
    确保与 ad_time_pricing_service 中的过滤逻辑完全一致。

    Args:
        strategy: 分时策略

    Returns:
        规则字典列表 [{"operateType": ..., "operateValue": ..., ...}]
    """
    time_settings = strategy.time_settings or {}
    if not isinstance(time_settings, dict):
        return []
    segments = time_settings.get("segments", [])
    time_mode = strategy.time_mode or "byDay"
    return get_rules_for_segments(segments, time_mode)


# ============================================================
# 主流程
# ============================================================


def _process_chunk(
    hit_chunk: list[AdTimePricingHit],
    strategy_map: dict[int, LxTimePricingStrategy],
    item_map: dict,
    now_utc: datetime,
) -> tuple[list[SpBidAdjustment], list[AdTimePricingHit], int, int, list[str]]:
    """线程入口：处理一批命中记录（纯内存计算）。

    #10：异常时递增 error_count，达到 MAX_ERROR_COUNT 后在 execute_time_pricing 中被跳过。
    """
    adjustments: list[SpBidAdjustment] = []
    hits_to_update: list[AdTimePricingHit] = []
    processed = 0
    adjusted = 0
    errors: list[str] = []

    for hit in hit_chunk:
        try:
            p, a = _process_single_hit(hit, strategy_map, item_map, now_utc, adjustments, hits_to_update)
            processed += p
            adjusted += a
            # 处理成功时重置 error_count（#10）
            if hit.error_count > 0:
                hit.error_count = 0
                hits_to_update.append(hit)
        except Exception:
            logger.exception("[time_pricing] campaign=%d profile=%d", hit.campaign_id, hit.profile_id)
            # #10：递增错误计数，追加到 update 列表
            hit.error_count = (hit.error_count or 0) + 1
            hit.updated_at = datetime.now(dt_timezone.utc)
            hits_to_update.append(hit)
            errors.append(f"campaign={hit.campaign_id} profile={hit.profile_id}")

    return adjustments, hits_to_update, processed, adjusted, errors


def _process_single_hit(
    hit: AdTimePricingHit,
    strategy_map: dict[int, LxTimePricingStrategy],
    item_map: dict,
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
    hits_to_update: list[AdTimePricingHit],
) -> tuple[int, int]:
    """处理单条命中记录，判断是否需要分时开始、回调或兜底重置。"""
    strategy = strategy_map.get(int(hit.hit_time_pricing_rules))
    if not strategy:
        # #9：策略不存在时清空 hit_time_pricing_rules，避免无限告警循环
        logger.warning("[time_pricing] 策略不存在 campaign=%d profile=%d rule_id=%s，清空规则等待重新匹配",
                       hit.campaign_id, hit.profile_id, hit.hit_time_pricing_rules)
        hit.hit_time_pricing_rules = ""
        hit.awaiting_start = TimePricingHitStatus.YES
        hit.is_time_pricing = TimePricingHitStatus.NO
        hit.rule_updated_today = False
        hit.updated_at = datetime.now(dt_timezone.utc)
        hits_to_update.append(hit)
        return 0, 0

    items = get_ad_items(hit.campaign_id, hit.profile_id, hit.targeting_type, item_map)
    if not items:
        logger.warning("[time_pricing] 无投放项 campaign=%d profile=%d", hit.campaign_id, hit.profile_id)
        return 0, 0

    in_period = _in_time_range(hit)
    is_awaiting = (hit.awaiting_start == TimePricingHitStatus.YES)

    # ── 路径 A：分时开始 ──
    if is_awaiting and in_period:
        return _do_start(hit, strategy, items, now_utc, adjustments, hits_to_update)

    # ── 路径 B：分时回调 ──
    need_callback = (not is_awaiting) and (not in_period)
    if need_callback:
        return _do_callback(hit, strategy, items, now_utc, adjustments, hits_to_update)

    # ── 路径 C：兜底重置（#1 防止 rule_updated_today 永久卡 True）──
    if is_awaiting and (not in_period) and hit.rule_updated_today:
        logger.info(
            "[time_pricing] campaign=%d profile=%d 时段已过且从未触发 _do_start，兜底重置 rule_updated_today",
            hit.campaign_id, hit.profile_id,
        )
        hit.rule_updated_today = False
        hit.updated_at = datetime.now(dt_timezone.utc)
        hits_to_update.append(hit)
        return 0, 0

    return 0, 0


def _do_start(
    hit: AdTimePricingHit,
    strategy: LxTimePricingStrategy,
    items: list[dict[str, Any]],
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
    hits_to_update: list[AdTimePricingHit],
) -> tuple[int, int]:
    """分时开始：计算降价并收集调整记录。

    #5：优先使用 seg 子时段精确匹配的规则，降级为全局合并规则。
    """
    from api_v2.services.ad_rules.time_pricing_calculator import append_start_adjustment

    rules = _get_active_rules(strategy)

    for item in items:
        item["bid_before"] = item["bid"]
        bid_after = round(item["bid"], 2)
        for rule in rules:
            nb = calc_new_bid(bid_after, rule)
            if nb is not None and nb != bid_after:
                bid_after = round(nb, 2)
        item["bid_after"] = bid_after
        append_start_adjustment(item, hit.campaign_id, hit.profile_id, strategy.id, now_utc, adjustments)

    hit.is_time_pricing = TimePricingHitStatus.YES
    hit.awaiting_start = TimePricingHitStatus.NO
    hit.rule_updated_today = False
    hit.error_count = 0  # #10：成功时重置错误计数
    hit.updated_at = datetime.now(dt_timezone.utc)  # #2：bulk_update 不触发 auto_now
    hits_to_update.append(hit)
    return 1, len(items)


def _do_callback(
    hit: AdTimePricingHit,
    strategy: LxTimePricingStrategy,
    items: list[dict[str, Any]],
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
    hits_to_update: list[AdTimePricingHit],
) -> tuple[int, int]:
    """分时回调：正算分时竞价，与基准值比对判断是否需要回调。

    核心逻辑（与 _do_start 完全相同的正算方式）：
      1. 用分时规则对基准值（item["bid"]）正向计算分时竞价。
      2. 分时竞价 = 调整前（bid_before），基准值 = 调整后（bid_after）。
      3. 若 bid_before == bid_after → 竞价不变，标 SUCCESS。
      4. 若 bid_before != bid_after → 需要回调，标 PENDING。
    """
    from api_v2.services.ad_rules.time_pricing_calculator import append_callback_adjustment

    callback = strategy.callback_settings or {}
    if callback.get("type", "none") == "none":
        hit.awaiting_start = TimePricingHitStatus.YES
        hit.is_time_pricing = TimePricingHitStatus.NO
        hit.rule_updated_today = False
        hit.updated_at = datetime.now(dt_timezone.utc)
        hits_to_update.append(hit)
        return 1, 0

    rules = _get_active_rules(strategy)
    adjusted_items = 0

    for item in items:
        base_bid = item["bid"]  # 调整后 = 基准值

        # 正算分时竞价：得到调整前 = 分时竞价
        priced_bid = round(base_bid, 2)
        for rule in rules:
            nb = calc_new_bid(priced_bid, rule)
            if nb is not None and nb != priced_bid:
                priced_bid = round(nb, 2)

        item["bid_before"] = priced_bid  # 调整前 = 分时竞价
        item["bid_after"] = base_bid     # 调整后 = 基准值

        append_callback_adjustment(
            item, base_bid,  # 回调目标 = 基准值
            hit.campaign_id, hit.profile_id, strategy.id, now_utc, adjustments,
        )
        adjusted_items += 1

    hit.awaiting_start = TimePricingHitStatus.YES
    hit.is_time_pricing = TimePricingHitStatus.NO
    hit.rule_updated_today = False
    hit.error_count = 0
    hit.updated_at = datetime.now(dt_timezone.utc)
    hits_to_update.append(hit)
    return 1, adjusted_items


def execute_time_pricing() -> dict[str, Any]:
    """并行处理所有 AdTimePricingHit 记录，执行分时开始、回调或兜底重置。

    优化策略：
      1. 先拦截需要兜底重置的记录（#1）、无效策略的记录（#9）和失败过多的记录（#10）
      2. 对 awaiting_start + _in_time_range 快速筛选需要处理的 hits
      3. 仅对需要处理的 hits 构建 item_map（减少 DB 查询范围）
      4. 32 线程并行处理
      5. 事务保护批量写入（#3）

    Returns:
        {"processed": int, "adjusted": int, "errors": list[str]}
    """
    t0 = datetime.now()
    all_hits = list(AdTimePricingHit.objects.filter(hit_time_pricing_rules__gt=""))
    if not all_hits:
        logger.info("[time_pricing] 无记录")
        return {"processed": 0, "adjusted": 0, "errors": []}

    logger.info("[time_pricing] 全量记录数=%d 开始筛选需要处理的 hits", len(all_hits))

    # ── 第一步：加载策略 + 快速筛选 + 拦截清理（纯内存，无 DB）──
    strategy_ids = {int(h.hit_time_pricing_rules) for h in all_hits if h.hit_time_pricing_rules}
    strategy_map = {
        s.id: s for s in LxTimePricingStrategy.objects.filter(pk__in=strategy_ids)
    }
    logger.info("[time_pricing] 策略加载=%d 耗时=%.1fs", len(strategy_map), (datetime.now() - t0).total_seconds())

    need_process: list[AdTimePricingHit] = []
    stale_cleanup: list[AdTimePricingHit] = []  # 兜底重置 + 策略失效，需批量写入

    for hit in all_hits:
        # #10：跳过连续失败过多的记录
        if hit.error_count and hit.error_count >= MAX_ERROR_COUNT:
            if hit.error_count % MAX_ERROR_COUNT == 0:
                logger.error(
                    "[time_pricing] campaign=%d profile=%d error_count=%d 已达到阈值，跳过处理",
                    hit.campaign_id, hit.profile_id, hit.error_count,
                )
            continue

        if int(hit.hit_time_pricing_rules) not in strategy_map:
            # #9：策略 ID 无效 → 清空规则，等待重新匹配
            logger.warning("[time_pricing] 策略不存在 campaign=%d profile=%d rule_id=%s",
                           hit.campaign_id, hit.profile_id, hit.hit_time_pricing_rules)
            hit.hit_time_pricing_rules = ""
            hit.awaiting_start = TimePricingHitStatus.YES
            hit.is_time_pricing = TimePricingHitStatus.NO
            hit.rule_updated_today = False
            hit.updated_at = datetime.now(dt_timezone.utc)
            stale_cleanup.append(hit)
            continue

        in_period = _in_time_range(hit)
        is_awaiting = (hit.awaiting_start == TimePricingHitStatus.YES)

        if is_awaiting and in_period:
            need_process.append(hit)
        elif not is_awaiting and not in_period:
            need_process.append(hit)
        elif is_awaiting and not in_period and hit.rule_updated_today:
            # #1 兜底路径：时段已过且从未触发 _do_start，重置标记防止永久卡死
            logger.info(
                "[time_pricing] campaign=%d profile=%d 时段已过 + 兜底重置 rule_updated_today",
                hit.campaign_id, hit.profile_id,
            )
            hit.rule_updated_today = False
            hit.updated_at = datetime.now(dt_timezone.utc)
            stale_cleanup.append(hit)

    # 先批量写入清理记录（策略不存在 + 兜底重置）
    if stale_cleanup:
        AdTimePricingHit.objects.bulk_update(
            stale_cleanup,
            [
                "awaiting_start",
                "is_time_pricing",
                "hit_time_pricing_rules",
                "rule_updated_today",
                "error_count",
                "updated_at",
            ],
            batch_size=500,
        )

    logger.info("[time_pricing] 筛选完成 需处理=%d 清理=%d/%d 耗时=%.1fs",
                len(need_process), len(stale_cleanup), len(all_hits),
                (datetime.now() - t0).total_seconds())

    if not need_process:
        logger.info("[time_pricing] 无需处理的记录")
        return {"processed": 0, "adjusted": 0, "errors": []}

    # ── 第二步：仅对需要处理的 hits 构建 item_map ──
    item_map = build_item_map({(h.campaign_id, h.profile_id) for h in need_process})
    logger.info("[time_pricing] item_map 构建完成=%d campaigns 耗时=%.1fs",
                len(item_map), (datetime.now() - t0).total_seconds())

    # ── 第三步：多线程并行处理 ──
    # 注意：应用服务器单 worker 内存有限，线程数必须克制，
    #       数据量大时宁可慢一点也不能 OOM Kill
    now_utc = datetime.now(dt_timezone.utc)
    MAX_WORKERS = min(8, len(need_process))
    chunk_size = max(1, len(need_process) // MAX_WORKERS) if MAX_WORKERS > 0 else len(need_process)
    chunks = [need_process[i:i + chunk_size] for i in range(0, len(need_process), chunk_size)][:MAX_WORKERS] if MAX_WORKERS > 0 else [need_process]
    logger.info("[time_pricing] 分 %d 个分片 %d 线程开始处理", len(chunks), MAX_WORKERS)

    adjustments, hits_to_update, processed, adjusted, errors = [], [], 0, 0, []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_process_chunk, c, strategy_map, item_map, now_utc) for c in chunks]
        for f in as_completed(futures):
            adjs, htus, pr, adj, errs = f.result()
            adjustments.extend(adjs)
            hits_to_update.extend(htus)
            processed += pr
            adjusted += adj
            errors.extend(errs)

    logger.info("[time_pricing] 线程处理完成 耗时=%.1fs", (datetime.now() - t0).total_seconds())

    # #3：事务保护写入
    write_batch(adjustments, hits_to_update)
    logger.info("[time_pricing] 完成 processed=%d adjusted=%d errors=%d 总耗时=%.1fs",
                processed, adjusted, len(errors), (datetime.now() - t0).total_seconds())
    return {"processed": processed, "adjusted": adjusted, "errors": errors}
