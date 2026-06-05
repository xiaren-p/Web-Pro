"""分时策略执行器（time_pricing_service）。

两个阶段合并为一个服务：
  - 分时开始：is_callback=1（已回调）+ 当前在时段内 → 写 START + is_time_pricing=YES + is_callback=0 + rule_updated_today=0
  - 分时回调：is_callback=0（未回调）+ 当前不在时段内 → 写 CALLBACK + is_time_pricing=NO + is_callback=1

时段判断：
  直接使用 AdTimePricingHit 的 time_start_cn / time_end_cn 字段（北京时区 naive datetime），
  与当前北京时间比对，无需重复解析策略 time_settings。
  上游 ad_time_pricing_service 在写入命中记录时已计算好四个时间值。

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
from datetime import datetime, timezone as dt_timezone
from typing import Any

from zoneinfo import ZoneInfo

from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.models.sp_bid_adjustment import SpBidAdjustment
from api_v2.services.ad_rules.time_pricing_calculator import (
    build_item_map, calc_callback_bid, calc_new_bid, get_ad_items, write_batch,
)

logger = logging.getLogger(__name__)

# 北京时间
_TZ_CN = ZoneInfo("Asia/Shanghai")


# ============================================================
# 时段判断
# ============================================================

def _in_time_range(hit: AdTimePricingHit) -> bool:
    """判断当前北京时间是否在命中记录的时段内。

    直接用 ad_time_pricing_hit 表已计算好的 time_start_cn / time_end_cn，
    与当前北京时间比对，无需重复解析策略 time_settings。

    Args:
        hit: 分时命中记录（含 time_start_cn / time_end_cn）

    Returns:
        True 表示当前在时段内
    """
    if hit.time_start_cn is None or hit.time_end_cn is None:
        return False
    now_cn = datetime.now(_TZ_CN).replace(tzinfo=None)
    return hit.time_start_cn <= now_cn <= hit.time_end_cn


# ============================================================
# 规则获取
# ============================================================

def _get_active_rules(strategy: LxTimePricingStrategy) -> list[dict]:
    """从策略 time_settings 中提取所有时段的所有规则（不做时间匹配）。

    时间匹配已在写入 AdTimePricingHit 时完成（time_start/time_end），
    此处只需取出规则列表用于竞价计算。

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

def _preload_data(
    hits: list[AdTimePricingHit],
) -> tuple[dict, dict[int, LxTimePricingStrategy]]:
    """预加载投放项和策略数据。投放项按 (campaign_id, profile_id) 分批 Q 查询，SQL 层过滤。"""
    item_map = build_item_map({(h.campaign_id, h.profile_id) for h in hits})
    strategy_ids = {int(h.hit_time_pricing_rules) for h in hits if h.hit_time_pricing_rules}
    strategy_map = {
        s.id: s for s in LxTimePricingStrategy.objects.filter(pk__in=strategy_ids)
    }
    logger.info("[time_pricing] 预加载: items=%d strategies=%d", len(item_map), len(strategy_map))
    return item_map, strategy_map


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
    """分时回调：按回调策略收集调整记录。"""
    from api_v2.services.ad_rules.time_pricing_calculator import append_callback_adjustment

    callback = strategy.callback_settings or {}
    if callback.get("type", "none") == "none":
        hit.is_callback = TimePricingHitStatus.YES
        hit.is_time_pricing = TimePricingHitStatus.NO
        hits_to_update.append(hit)
        return 1, 0

    for item in items:
        callback_bid = calc_callback_bid(item["bid"], callback)
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

    Returns:
        {"processed": int, "adjusted": int, "errors": list[str]}
    """
    hits = list(AdTimePricingHit.objects.filter(hit_time_pricing_rules__gt=""))
    if not hits:
        logger.info("[time_pricing] 无记录")
        return {"processed": 0, "adjusted": 0, "errors": []}

    logger.info("[time_pricing] 记录数=%d", len(hits))
    item_map, strategy_map = _preload_data(hits)

    now_utc = datetime.now(dt_timezone.utc)
    CHUNKS = 16
    chunk_size = max(1, len(hits) // CHUNKS)
    chunks = [hits[i:i + chunk_size] for i in range(0, len(hits), chunk_size)][:CHUNKS]

    adjustments, hits_to_update, processed, adjusted, errors = [], [], 0, 0, []

    with ThreadPoolExecutor(max_workers=CHUNKS) as executor:
        futures = [executor.submit(_process_chunk, c, strategy_map, item_map, now_utc) for c in chunks]
        for f in as_completed(futures):
            adjs, htus, pr, adj, errs = f.result()
            adjustments.extend(adjs); hits_to_update.extend(htus)
            processed += pr; adjusted += adj
            errors.extend(errs)

    write_batch(adjustments, hits_to_update)
    logger.info("[time_pricing] 完成 processed=%d adjusted=%d errors=%d", processed, adjusted, len(errors))
    return {"processed": processed, "adjusted": adjusted, "errors": errors}
