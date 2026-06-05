"""分时策略执行器（time_pricing_service）。

两个阶段合并为一个服务：
  - 分时开始：is_callback=1（已回调）+ 时段内 → 写 START + is_time_pricing=YES + is_callback=0 + rule_updated_today=0
  - 分时回调：is_callback=0（未回调）+ 不在时段内 → 写 CALLBACK + is_time_pricing=NO + is_callback=1

完整执行链路（顺序不可颠倒）：
  ① _preload_data()：预加载策略到内存 map（投放项改为每条 hit 实时 SQL 查，不扫全表）
  ② _process_single_hit()：fetch_ad_items() 实时按 (campaign_id, profile_id, targeting_type) 查 DB
     → 判断时段 → 分流到 _do_start / _do_callback
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

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.models.sp_bid_adjustment import SpBidAdjustment
from api_v2.services.ad_rules.time_pricing_calculator import (
    calc_callback_bid, calc_new_bid, fetch_ad_items, write_batch,
)

logger = logging.getLogger(__name__)


# ============================================================
# 时间判断
# ============================================================

def _get_local_time_str(tz_name: str) -> str | None:
    """获取指定时区的当前时间 HH:MM。"""
    if not tz_name:
        return None
    try:
        return datetime.now(ZoneInfo(tz_name)).strftime("%H:%M")
    except ZoneInfoNotFoundError:
        logger.warning("[time_pricing] 未知时区: %s", tz_name)
        return None


def _find_matching_rules(
    time_settings: dict, tz_name: str, time_mode: str = "byDay",
) -> list[dict]:
    """在策略的 time_settings 中查找当前时间命中的所有规则。"""
    local_time = _get_local_time_str(tz_name)
    if local_time is None:
        return []

    segments = (time_settings or {}).get("segments", []) if isinstance(time_settings, dict) else []
    if time_mode == "calendar":
        return []

    matching_rules: list[dict] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        start = seg.get("startTime", "")
        end = seg.get("endTime", "")
        if not start or not end:
            continue

        in_range = start <= local_time <= end
        if not in_range and start > end:
            in_range = local_time >= start or local_time <= end
        if not in_range:
            continue

        if time_mode == "byWeek":
            day_of_week = seg.get("dayOfWeek", "")
            if day_of_week:
                try:
                    weekday = str(datetime.now(ZoneInfo(tz_name)).isoweekday())
                    if weekday != str(day_of_week):
                        continue
                except ZoneInfoNotFoundError:
                    continue

        rules = seg.get("rules", [])
        if isinstance(rules, list):
            matching_rules.extend(rules)

    return matching_rules


# ============================================================
# 主流程
# ============================================================

def _preload_data(
    hits: list[AdTimePricingHit],
) -> dict[int, LxTimePricingStrategy]:
    """预加载策略数据。投放项改为每条 hit 实时 SQL 查询，不再全表扫内存。"""
    strategy_ids = {int(h.hit_time_pricing_rules) for h in hits if h.hit_time_pricing_rules}
    strategy_map = {
        s.id: s for s in LxTimePricingStrategy.objects.filter(pk__in=strategy_ids)
    }
    logger.info("[time_pricing] strategies=%d", len(strategy_map))
    return strategy_map


def _process_chunk(
    hit_chunk: list[AdTimePricingHit],
    strategy_map: dict[int, LxTimePricingStrategy],
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
            p, a = _process_single_hit(hit, strategy_map, now_utc, adjustments, hits_to_update)
            processed += p; adjusted += a
        except Exception:
            logger.exception("[time_pricing] campaign=%d", hit.campaign_id)
            errors.append(f"campaign={hit.campaign_id} profile={hit.profile_id}")

    return adjustments, hits_to_update, processed, adjusted, errors


def _process_single_hit(
    hit: AdTimePricingHit,
    strategy_map: dict[int, LxTimePricingStrategy],
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
    hits_to_update: list[AdTimePricingHit],
) -> tuple[int, int]:
    """处理单条命中记录，判断是否需要分时开始或回调。"""
    strategy = strategy_map.get(int(hit.hit_time_pricing_rules))
    if not strategy:
        logger.warning("[time_pricing] 策略不存在 campaign=%d", hit.campaign_id)
        return 0, 0

    items = fetch_ad_items(hit.campaign_id, hit.profile_id, hit.targeting_type)
    if not items:
        logger.warning("[time_pricing] 无投放项 campaign=%d", hit.campaign_id)
        return 0, 0

    in_period = len(_find_matching_rules(
        strategy.time_settings or {}, hit.timezone or "", strategy.time_mode,
    )) > 0

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
        for rule in _find_matching_rules(
            strategy.time_settings or {}, hit.timezone or "", strategy.time_mode,
        ):
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
    strategy_map = _preload_data(hits)

    now_utc = datetime.now(dt_timezone.utc)
    CHUNKS = 16
    chunk_size = max(1, len(hits) // CHUNKS)
    chunks = [hits[i:i + chunk_size] for i in range(0, len(hits), chunk_size)][:CHUNKS]

    adjustments, hits_to_update, processed, adjusted, errors = [], [], 0, 0, []

    with ThreadPoolExecutor(max_workers=CHUNKS) as executor:
        futures = [executor.submit(_process_chunk, c, strategy_map, now_utc) for c in chunks]
        for f in as_completed(futures):
            adjs, htus, pr, adj, errs = f.result()
            adjustments.extend(adjs); hits_to_update.extend(htus)
            processed += pr; adjusted += adj
            errors.extend(errs)

    write_batch(adjustments, hits_to_update)
    logger.info("[time_pricing] 完成 processed=%d adjusted=%d errors=%d", processed, adjusted, len(errors))
    return {"processed": processed, "adjusted": adjusted, "errors": errors}
