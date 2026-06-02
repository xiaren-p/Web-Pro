"""分时策略执行器（time_pricing_executor）。

职责：
  1. 遍历 AdTimePricingHit 中待分时的记录
  2. 根据命中策略的 time_settings 判断当前时段是否匹配
  3. 按投放类型（auto/manual）查询 LxSpTarget / LxSpKeyword
  4. 应用分时规则计算调整后竞价
  5. 写入 SpBidAdjustment 表并更新 AdTimePricingHit.is_time_pricing

时间判断基于 AdTimePricingHit.timezone 字段（如 "America/Los_Angeles"）。
不区分冬夏令时——始终以 UTC 偏移计算当地时间的 HH:MM。
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone as dt_timezone
from typing import Any

from django.db.models import Q

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api_v1.models.lingxing.ads.basic.lx_sp_keyword import LxSpKeyword
from api_v1.models.lingxing.ads.basic.lx_sp_target import LxSpTarget
from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices, ExecutionStatusChoices, ExecutionTypeChoices, SpBidAdjustment,
)

logger = logging.getLogger(__name__)


# ============================================================
# 竞价规则计算
# ============================================================

def _calc_new_bid(current_bid: float, rule: dict) -> float | None:
    """根据单条规则计算调整后的竞价。

    Args:
        current_bid: 当前竞价
        rule: {"operateType", "operateValue", "limitValue", "triggerValue", "targetValue"}

    Returns:
        调整后竞价；若 bid_above/below 条件不满足则返回 None（不调整）
    """
    op = rule.get("operateType", "")
    val = float(rule.get("operateValue", 0) or 0)
    lim = float(rule.get("limitValue", 0) or 0)
    trig = float(rule.get("triggerValue", 0) or 0)
    tgt = float(rule.get("targetValue", 0) or 0)

    if op == "percent_decrease":
        return max(current_bid * (1 - val), lim) if val else current_bid
    if op == "percent_increase":
        return min(current_bid * (1 + val), lim) if val else current_bid
    if op == "fixed_decrease":
        return max(current_bid - val, lim)
    if op == "fixed_increase":
        return min(current_bid + val, lim)
    if op == "fixed":
        return val
    if op == "bid_above_fixed":
        return tgt if current_bid > trig else None
    if op == "bid_below_fixed":
        return tgt if current_bid < trig else None
    return None


# ============================================================
# 时间匹配
# ============================================================

def _get_local_time_str(tz_name: str) -> str | None:
    """获取指定时区的当前时间 HH:MM 字符串。

    不区分冬夏令时——始终以 ZoneInfo 时区转换。

    Args:
        tz_name: 时区名称，如 "America/Los_Angeles"

    Returns:
        "HH:MM" 字符串，若时区无效则返回 None
    """
    if not tz_name:
        return None
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning("[time_pricing_executor] 未知时区: %s", tz_name)
        return None
    now_local = datetime.now(tz)
    return now_local.strftime("%H:%M")


def _find_matching_rules(
    time_settings: dict, tz_name: str, time_mode: str = "byDay",
) -> list[dict]:
    """在策略的 time_settings 中查找当前时间命中的所有规则。

    Args:
        time_settings: 策略的 time_settings JSON 字段
        tz_name: 记录时区
        time_mode: 策略的 time_mode 字段（"byDay"/"byWeek"/"calendar"）

    Returns:
        当前命中的所有规则列表（可能跨多个时间段），未命中返回空列表
    """
    local_time = _get_local_time_str(tz_name)
    if local_time is None:
        return []

    mode = time_mode
    segments = (time_settings or {}).get("segments", []) if isinstance(time_settings, dict) else []

    if mode == "calendar":
        # 日历模式暂不处理
        logger.debug("[time_pricing_executor] 日历模式暂不支持")
        return []

    matching_rules: list[dict] = []

    for seg in segments:
        if not isinstance(seg, dict):
            continue
        start = seg.get("startTime", "")
        end = seg.get("endTime", "")
        if not start or not end:
            continue

        # 时间区间匹配
        in_range = start <= local_time <= end
        # 处理跨夜情况（如 22:00 ~ 02:00）
        if not in_range and start > end:
            in_range = local_time >= start or local_time <= end

        if not in_range:
            continue

        # dayOfWeek 仅在 byWeek 模式下检查，byDay 模式忽略
        if mode == "byWeek":
            day_of_week = seg.get("dayOfWeek", "")
            if day_of_week:
                try:
                    tz = ZoneInfo(tz_name)
                    weekday = str(datetime.now(tz).isoweekday())
                    if weekday != str(day_of_week):
                        continue
                except ZoneInfoNotFoundError:
                    continue

        # 该时间段的所有规则都加入
        rules = seg.get("rules", [])
        if isinstance(rules, list):
            matching_rules.extend(rules)

    return matching_rules


# ============================================================
# 批量预加载投放项（target / keyword）→ 内存映射
# ============================================================

def _build_item_map(
    campaign_keys: set[tuple[int, int]],
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """批量查询所有 target 和 keyword，按 (campaign_id, profile_id) 建立内存映射。

    一次查询全量 LxSpTarget + LxSpKeyword，避免逐条 N+1。

    Args:
        campaign_keys: 需要查询的 (campaign_id, profile_id) 集合

    Returns:
        {(campaign_id, profile_id): [{"item_type", "item_id", "ad_group_id", "bid"}]}
    """
    item_map: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)

    # 收集所有需要查询的 campaign 对
    pairs_list = list(campaign_keys)

    # 批量查 target（auto）
    if pairs_list:
        q_target = Q()
        for cid, pid in pairs_list:
            q_target |= Q(campaign_id=cid, profile_id=pid)
        for t in LxSpTarget.objects.filter(q_target).iterator():
            if t.bid is not None:
                item_map[(t.campaign_id, t.profile_id)].append({
                    "item_type": "target",
                    "item_id": t.target_id,
                    "ad_group_id": t.ad_group_id,
                    "bid": float(t.bid),
                })

    # 批量查 keyword（manual）
    if pairs_list:
        q_kw = Q()
        for cid, pid in pairs_list:
            q_kw |= Q(campaign_id=cid, profile_id=pid)
        for k in LxSpKeyword.objects.filter(q_kw).iterator():
            if k.bid is not None:
                item_map[(k.campaign_id, k.profile_id)].append({
                    "item_type": "keyword",
                    "item_id": k.keyword_id,
                    "ad_group_id": k.ad_group_id,
                    "bid": float(k.bid),
                })

    return item_map


def _get_ad_items(
    campaign_id: int, profile_id: int, targeting_type: str,
    item_map: dict[tuple[int, int], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """从预加载的内存映射中获取投放项（不查 DB）。

    Args:
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID
        targeting_type: 投放类型（"auto" / "manual"）
        item_map: _build_item_map 构建的内存映射

    Returns:
        [{"item_type": "target"/"keyword", "item_id": int, "ad_group_id": int, "bid": float}]
    """
    return item_map.get((campaign_id, profile_id), [])


# ============================================================
# 主流程
# ============================================================

def _preload_start_data(
    hits: list[AdTimePricingHit],
) -> tuple[dict[tuple[int, int], list[dict[str, Any]]], dict[int, LxTimePricingStrategy]]:
    """批量预加载分时开始所需的投放项和策略数据。

    Args:
        hits: 待处理的命中记录列表

    Returns:
        (item_map, strategy_map) 元组
    """
    item_map = _build_item_map({(h.campaign_id, h.profile_id) for h in hits})
    strategy_ids = {int(h.hit_time_pricing_rules) for h in hits if h.hit_time_pricing_rules}
    strategy_map = {
        s.id: s for s in LxTimePricingStrategy.objects.filter(pk__in=strategy_ids).only(
            "id", "shops", "time_mode", "time_settings", "callback_settings",
        )
    }
    logger.info("[time_pricing_executor] 预加载: items=%d strategies=%d", len(item_map), len(strategy_map))
    return item_map, strategy_map


def _process_start_for_hit(
    hit: AdTimePricingHit, strategy: LxTimePricingStrategy,
    item_map: dict, now_utc: datetime, adjustments: list[SpBidAdjustment],
) -> int:
    """处理单条命中记录，计算竞价并收集调整记录。

    Returns:
        实际发生竞价变化的投放项数；0 表示无匹配规则或无投放项。
    """
    matching_rules = _find_matching_rules(strategy.time_settings or {}, hit.timezone or "", strategy.time_mode)
    if not matching_rules:
        return 0
    items = _get_ad_items(hit.campaign_id, hit.profile_id, hit.targeting_type, item_map)
    if not items:
        return 0
    changed = 0
    for item in items:
        bid_after = item["bid"]
        for rule in matching_rules:
            nb = _calc_new_bid(bid_after, rule)
            if nb is not None and nb != bid_after:
                bid_after = nb
        if bid_after == item["bid"]:
            continue
        is_target = item["item_type"] == "target"
        adjustments.append(SpBidAdjustment(
            target_id=item["item_id"] if is_target else None,
            keyword_id=item["item_id"] if not is_target else None,
            campaign_id=hit.campaign_id, profile_id=hit.profile_id,
            execution_type=ExecutionTypeChoices.TIME_PRICING_START,
            time_pricing_rule_id=strategy.id, auto_rule_id=None,
            is_time_pricing=TimePricingHitStatus.YES,
            bid_before=item["bid"], bid_after=bid_after,
            adjustment_status=AdjustmentStatusChoices.PENDING,
            adjustment_time=now_utc,
            execution_status=ExecutionStatusChoices.PENDING,
        ))
        changed += 1
    return changed


def _write_start_batch(adjustments: list, hits_to_update: list) -> None:
    """批量写入 SpBidAdjustment 和 AdTimePricingHit。

    Args:
        adjustments: 待写入的调整记录列表
        hits_to_update: 待更新 is_time_pricing 的记录列表
    """
    if adjustments:
        SpBidAdjustment.objects.bulk_create(adjustments, batch_size=500)
    if hits_to_update:
        AdTimePricingHit.objects.bulk_update(hits_to_update, ["is_time_pricing", "updated_at"], batch_size=500)


def execute_time_pricing_start() -> dict[str, Any]:
    """执行"分时开始"：批量预加载 → 遍历匹配 → 批量写入。

    Returns:
        {"processed": int, "adjusted": int, "errors": list[str]}
    """
    hits = list(AdTimePricingHit.objects.filter(
        is_time_pricing=TimePricingHitStatus.NO, hit_time_pricing_rules__gt="",
    ))
    if not hits:
        logger.info("[time_pricing_executor] 无待分时记录")
        return {"processed": 0, "adjusted": 0, "errors": []}

    logger.info("[time_pricing_executor] 待分时记录数=%d", len(hits))
    item_map, strategy_map = _preload_start_data(hits)

    now_utc = datetime.now(dt_timezone.utc)
    adjustments: list[SpBidAdjustment] = []
    hits_to_update: list[AdTimePricingHit] = []
    processed = 0
    adjusted = 0
    errors: list[str] = []

    for hit in hits:
        try:
            strategy = strategy_map.get(int(hit.hit_time_pricing_rules))
            if not strategy:
                hit.is_time_pricing = TimePricingHitStatus.YES
                hits_to_update.append(hit)
                processed += 1
                continue

            changed = _process_start_for_hit(hit, strategy, item_map, now_utc, adjustments)
            hit.is_time_pricing = TimePricingHitStatus.YES
            hits_to_update.append(hit)
            adjusted += changed
            processed += 1

        except Exception:
            logger.exception("[time_pricing_executor] campaign=%d", hit.campaign_id)
            errors.append(f"campaign={hit.campaign_id} profile={hit.profile_id}")

    _write_start_batch(adjustments, hits_to_update)
    logger.info("[time_pricing_executor] 完成 processed=%d adjusted=%d errors=%d", processed, adjusted, len(errors))
    return {"processed": processed, "adjusted": adjusted, "errors": errors}
