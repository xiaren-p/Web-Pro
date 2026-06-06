"""分时策略执行器（time_pricing_service）。

两个阶段合并为一个服务：
  - 分时开始：is_callback=1（已回调）+ 当前在时段内 → 写 START + is_time_pricing=YES + is_callback=0 + rule_updated_today=0
  - 分时回调：is_callback=0（未回调）+ 当前不在时段内 → 写 CALLBACK + is_time_pricing=NO + is_callback=1

时段判断：
  直接使用 AdTimePricingHit 的 time_start_cn / time_end_cn 字段（北京时间 aware datetime，固定偏移 +8），
  与当前北京时间比对，无需重复解析策略 time_settings。
  上游 ad_time_pricing_service 在写入命中记录时已根据规则时段 + 站点 UTC 偏移算好四个时间值。
  多时段时取所有时段的最小 start 和最大 end 合并为一个覆盖窗口。

完整执行链路：
  ① _preload_data()：预加载策略 + 投放项（投放项按 campaign_keys 分批 Q 对象 SQL 查询）
  ② _process_single_hit()：从内存 item_map 取投放项 → 用 hit.time_start_cn / time_end_cn 判断时段 → 分流
  ③ _do_start / _do_callback：纯内存计算竞价 → 收集 SpBidAdjustment + AdTimePricingHit 待写列表
  ④ write_batch()：先 bulk_create(SpBidAdjustment) → 再 bulk_update(AdTimePricingHit 状态)

处理流程：
  ├─ is_callback=1（已回调）+ 在时段内 → _do_start()
  │   ├─ 取原始竞价(bid_before=当前实时竞价)
  │   ├─ 规则链式计算 bid_after
  │   ├─ append_start_adjustment()
  │   │   ├─ bid_before==bid_after → 标 SUCCESS，msg="竞价相等无需调整"
  │   │   └─ 不等 → 标 PENDING，待 bid_adjustment 调 API
  │   └─ UPDATE hit: is_time_pricing=YES, is_callback=NO, rule_updated_today=False
  │
  └─ is_callback=0（未回调）+ 不在时段内 → _do_callback()
      ├─ callback.type=none → 只改状态
      ├─ 每条 item 计算回调竞价
      ├─ append_callback_adjustment()
      │   ├─ 回调竞价==原始竞价(bid_before) → 跳过不写
      │   └─ 不等 → 写 PENDING CALLBACK 记录
      └─ UPDATE hit: is_callback=YES, is_time_pricing=NO
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
    build_item_map, calc_callback_bid, calc_new_bid, get_ad_items, write_batch,
)

logger = logging.getLogger(__name__)


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


# ============================================================
# 规则获取
# ============================================================

def _get_active_rules(strategy: LxTimePricingStrategy) -> list[dict]:
    """从策略 time_settings 中提取今天适用的规则（按 dayOfWeek 过滤）。

    三种模式：
      - byDay：所有时段全部适用
      - byWeek：只取 dayOfWeek 等于今天周几的时段
      - calendar：所有时段全适用（暂不支持 grid 格式）

    Args:
        strategy: 分时策略

    Returns:
        规则字典列表 [{"operateType": ..., "operateValue": ..., ...}]
    """
    time_settings = strategy.time_settings or {}
    if not isinstance(time_settings, dict):
        return []
    segments = time_settings.get("segments", [])
    if not isinstance(segments, list):
        return []

    time_mode = strategy.time_mode or "byDay"

    # byWeek：按 dayOfWeek 过滤
    if time_mode == "byWeek":
        today_weekday = str(datetime.now(dt_timezone(timedelta(hours=8))).isoweekday())  # 北京时间周几
        segments = [
            seg for seg in segments
            if isinstance(seg, dict) and str(seg.get("dayOfWeek", "")) == today_weekday
        ]

    rules: list[dict] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        seg_rules = seg.get("rules", [])
        if isinstance(seg_rules, list):
            rules.extend(seg_rules)
    return rules


# ============================================================
# 主流程
# ============================================================



def _process_chunk(
    hit_chunk: list[AdTimePricingHit],
    strategy_map: dict[int, LxTimePricingStrategy],
    item_map: dict,
    now_utc: datetime,
) -> tuple[list[SpBidAdjustment], list[AdTimePricingHit], int, int, list[str]]:
    """线程入口：处理一批命中记录（纯内存计算）。"""
    adjustments: list[SpBidAdjustment] = []
    hits_to_update: list[AdTimePricingHit] = []
    processed = 0
    adjusted = 0
    errors: list[str] = []

    for hit in hit_chunk:
        try:
            p, a = _process_single_hit(hit, strategy_map, item_map, now_utc, adjustments, hits_to_update)
            processed += p; adjusted += a
        except Exception:
            logger.exception("[time_pricing] campaign=%d", hit.campaign_id)
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
    """处理单条命中记录，判断是否需要分时开始或回调。"""
    strategy = strategy_map.get(int(hit.hit_time_pricing_rules))
    if not strategy:
        logger.warning("[time_pricing] 策略不存在 campaign=%d", hit.campaign_id)
        return 0, 0

    items = get_ad_items(hit.campaign_id, hit.profile_id, hit.targeting_type, item_map)
    if not items:
        logger.warning("[time_pricing] 无投放项 campaign=%d", hit.campaign_id)
        return 0, 0

    in_period = _in_time_range(hit)

    # is_callback=1：已回调，需要判断是否重新开启分时
    if hit.is_callback == TimePricingHitStatus.YES and in_period:
        return _do_start(hit, strategy, items, now_utc, adjustments, hits_to_update)

    # is_callback=0：未回调，需要判断是否需要回调
    need_callback = (hit.is_callback == TimePricingHitStatus.NO) and (not in_period)
    if need_callback:
        return _do_callback(hit, strategy, items, now_utc, adjustments, hits_to_update)

    return 0, 0


def _do_start(
    hit: AdTimePricingHit,
    strategy: LxTimePricingStrategy,
    items: list[dict[str, Any]],
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
    hits_to_update: list[AdTimePricingHit],
) -> tuple[int, int]:
    """分时开始：计算降价并收集调整记录。"""
    from api_v2.services.ad_rules.time_pricing_calculator import append_start_adjustment

    for item in items:
        item["bid_before"] = item["bid"]
        bid_after = item["bid"]
        for rule in _get_active_rules(strategy):
            nb = calc_new_bid(bid_after, rule)
            if nb is not None and nb != bid_after:
                bid_after = nb
        item["bid_after"] = bid_after
        append_start_adjustment(item, hit.campaign_id, hit.profile_id, strategy.id, now_utc, adjustments)

    hit.is_time_pricing = TimePricingHitStatus.YES
    hit.is_callback = TimePricingHitStatus.NO
    hit.rule_updated_today = False
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
    """分时回调：按回调策略计算恢复竞价并收集调整记录。

    注意：item["bid"] 是当前 DB 竞价（已被 _do_start 降价过），
    item["bid_before"] 在 _do_start 阶段已保存为原始竞价。
    calc_callback_bid 使用原始竞价 bid_before（而非当前 bid）作为计算基数，
    确保 previous 类型能正确恢复到分时前的竞价。
    """
    from api_v2.services.ad_rules.time_pricing_calculator import append_callback_adjustment

    callback = strategy.callback_settings or {}
    if callback.get("type", "none") == "none":
        hit.is_callback = TimePricingHitStatus.YES
        hit.is_time_pricing = TimePricingHitStatus.NO
        hits_to_update.append(hit)
        return 1, 0

    for item in items:
        # 以 _do_start 保存的原始竞价为基数计算回调目标，而非当前已被降价的 DB 竞价
        base_bid = item.get("bid_before", item["bid"])
        callback_bid = calc_callback_bid(base_bid, callback)
        if callback_bid is None:
            continue
        append_callback_adjustment(
            item, callback_bid, hit.campaign_id, hit.profile_id, strategy.id, now_utc, adjustments,
        )

    hit.is_callback = TimePricingHitStatus.YES
    hit.is_time_pricing = TimePricingHitStatus.NO
    hits_to_update.append(hit)
    return 1, len(items)


def execute_time_pricing() -> dict[str, Any]:
    """并行处理所有 AdTimePricingHit 记录，执行分时开始或回调。

    优化策略：
      1. 先按 is_callback + _in_time_range 快速筛选需要处理的 hits（无 DB 查询）
      2. 仅对需要处理的 hits 构建 item_map（减少 DB 查询范围）
      3. 32 线程并行处理

    Returns:
        {"processed": int, "adjusted": int, "errors": list[str]}
    """
    t0 = datetime.now()
    all_hits = list(AdTimePricingHit.objects.filter(hit_time_pricing_rules__gt=""))
    if not all_hits:
        logger.info("[time_pricing] 无记录")
        return {"processed": 0, "adjusted": 0, "errors": []}

    logger.info("[time_pricing] 全量记录数=%d 开始筛选需要处理的 hits", len(all_hits))

    # ── 第一步：快速筛选需要处理的记录（纯内存，无 DB）──
    strategy_ids = {int(h.hit_time_pricing_rules) for h in all_hits if h.hit_time_pricing_rules}
    strategy_map = {
        s.id: s for s in LxTimePricingStrategy.objects.filter(pk__in=strategy_ids)
    }
    logger.info("[time_pricing] 策略加载=%d 耗时=%.1fs", len(strategy_map), (datetime.now() - t0).total_seconds())

    need_process: list[AdTimePricingHit] = []
    for hit in all_hits:
        if int(hit.hit_time_pricing_rules) not in strategy_map:
            continue
        in_period = _in_time_range(hit)
        if hit.is_callback == TimePricingHitStatus.YES and in_period:
            need_process.append(hit)
        elif hit.is_callback == TimePricingHitStatus.NO and not in_period:
            need_process.append(hit)

    logger.info("[time_pricing] 筛选完成 需处理=%d/%d 耗时=%.1fs",
                len(need_process), len(all_hits), (datetime.now() - t0).total_seconds())

    if not need_process:
        logger.info("[time_pricing] 无需处理的记录")
        return {"processed": 0, "adjusted": 0, "errors": []}

    # ── 第二步：仅对需要处理的 hits 构建 item_map ──
    item_map = build_item_map({(h.campaign_id, h.profile_id) for h in need_process})
    logger.info("[time_pricing] item_map 构建完成=%d campaigns 耗时=%.1fs",
                len(item_map), (datetime.now() - t0).total_seconds())

    # ── 第三步：多线程并行处理 ──
    now_utc = datetime.now(dt_timezone.utc)
    MAX_WORKERS = 32
    chunk_size = max(1, len(need_process) // MAX_WORKERS)
    chunks = [need_process[i:i + chunk_size] for i in range(0, len(need_process), chunk_size)][:MAX_WORKERS]
    logger.info("[time_pricing] 分 %d 个分片 %d 线程开始处理", len(chunks), MAX_WORKERS)

    adjustments, hits_to_update, processed, adjusted, errors = [], [], 0, 0, []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_process_chunk, c, strategy_map, item_map, now_utc) for c in chunks]
        for f in as_completed(futures):
            adjs, htus, pr, adj, errs = f.result()
            adjustments.extend(adjs); hits_to_update.extend(htus)
            processed += pr; adjusted += adj
            errors.extend(errs)

    logger.info("[time_pricing] 线程处理完成 耗时=%.1fs", (datetime.now() - t0).total_seconds())

    write_batch(adjustments, hits_to_update)
    logger.info("[time_pricing] 完成 processed=%d adjusted=%d errors=%d 总耗时=%.1fs",
                processed, adjusted, len(errors), (datetime.now() - t0).total_seconds())
    return {"processed": processed, "adjusted": adjusted, "errors": errors}
