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
from datetime import datetime, timezone as dt_timezone
from typing import Any

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
    time_settings: dict, tz_name: str,
) -> list[dict]:
    """在策略的 time_settings 中查找当前时间命中的所有规则。

    Args:
        time_settings: 策略的 time_settings JSON 字段
        tz_name: 记录时区

    Returns:
        当前命中的所有规则列表（可能跨多个时间段），未命中返回空列表
    """
    local_time = _get_local_time_str(tz_name)
    if local_time is None:
        return []

    mode = time_settings.get("mode", "byDay") if isinstance(time_settings, dict) else "byDay"
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

        # 按周模式下检查 dayOfWeek
        day_of_week = seg.get("dayOfWeek", "")
        if day_of_week:
            try:
                tz = ZoneInfo(tz_name)
                weekday = str(datetime.now(tz).isoweekday())  # 1=Mon .. 7=Sun
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
# 查询待调整的广告投放（target / keyword）
# ============================================================

def _get_ad_items(
    campaign_id: int, profile_id: int, targeting_type: str,
) -> list[dict[str, Any]]:
    """按投放类型查询关联的广告投放项及其当前竞价。

    Args:
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID
        targeting_type: 投放类型（"auto" / "manual"）

    Returns:
        [{"item_type": "target"/"keyword", "item_id": int, "ad_group_id": int, "bid": float}]
    """
    items: list[dict[str, Any]] = []

    if targeting_type == "auto":
        qs = LxSpTarget.objects.filter(campaign_id=campaign_id, profile_id=profile_id)
        for t in qs:
            if t.bid is not None:
                items.append({
                    "item_type": "target",
                    "item_id": t.target_id,
                    "ad_group_id": t.ad_group_id,
                    "bid": float(t.bid),
                })

    elif targeting_type == "manual":
        qs = LxSpKeyword.objects.filter(campaign_id=campaign_id, profile_id=profile_id)
        for k in qs:
            if k.bid is not None:
                items.append({
                    "item_type": "keyword",
                    "item_id": k.keyword_id,
                    "ad_group_id": k.ad_group_id,
                    "bid": float(k.bid),
                })

    return items


# ============================================================
# 主流程
# ============================================================

def execute_time_pricing_start() -> dict[str, Any]:
    """执行"分时开始"：遍历待分时记录，匹配时间区间，计算并写入调整。

    Returns:
        {"processed": int, "adjusted": int, "errors": [str]}
    """
    # 1. 取待分时记录
    hits = AdTimePricingHit.objects.filter(
        is_time_pricing=TimePricingHitStatus.NO,
        hit_time_pricing_rules__gt="",  # 有命中策略
    )
    if not hits.exists():
        logger.info("[time_pricing_executor] 无待分时记录")
        return {"processed": 0, "adjusted": 0, "errors": []}

    logger.info("[time_pricing_executor] 待分时记录数=%d", hits.count())

    processed = 0
    adjusted = 0
    errors: list[str] = []

    for hit in hits:
        try:
            # 2. 加载命中的策略
            strategy_id = int(hit.hit_time_pricing_rules)
            strategy = LxTimePricingStrategy.objects.filter(pk=strategy_id).first()
            if not strategy:
                logger.warning("[time_pricing_executor] 策略不存在 id=%d，标记已处理", strategy_id)
                hit.is_time_pricing = TimePricingHitStatus.YES
                hit.save(update_fields=["is_time_pricing", "updated_at"])
                processed += 1
                continue

            time_settings = strategy.time_settings or {}
            tz = hit.timezone or ""

            # 3. 判断当前时间是否在分时时间段内
            matching_rules = _find_matching_rules(time_settings, tz)
            if not matching_rules:
                # 不在时段内，跳过等待下次（可能下个小时就匹配了）
                continue

            # 4. 按投放类型查询关联投放项
            items = _get_ad_items(hit.campaign_id, hit.profile_id, hit.targeting_type)
            if not items:
                # 无投放项，标记已处理避免无限重试
                hit.is_time_pricing = TimePricingHitStatus.YES
                hit.save(update_fields=["is_time_pricing", "updated_at"])
                processed += 1
                continue

            processed += 1

            # 5. 对每个投放项应用所有匹配规则，写出调整记录
            now_utc = datetime.now(dt_timezone.utc)
            for item in items:
                item_id = item["item_id"]
                bid_before = item["bid"]
                bid_after = bid_before

                # 多条规则链式叠加：每条规则基于上一条的结果继续计算
                for rule in matching_rules:
                    new_bid = _calc_new_bid(bid_after, rule)
                    if new_bid is not None and new_bid != bid_after:
                        bid_after = new_bid

                # 只有竞价实际变化才写记录
                if bid_after == bid_before:
                    continue

                is_target = item["item_type"] == "target"
                SpBidAdjustment.objects.create(
                    target_id=item_id if is_target else None,
                    keyword_id=item_id if not is_target else None,
                    campaign_id=hit.campaign_id,
                    profile_id=hit.profile_id,
                    targeting_type=hit.targeting_type,
                    execution_type=ExecutionTypeChoices.TIME_PRICING_START,
                    time_pricing_rule_id=strategy.id,
                    auto_rule_id=None,
                    is_time_pricing=TimePricingHitStatus.YES,
                    bid_before=bid_before,
                    bid_after=bid_after,
                    adjustment_status=AdjustmentStatusChoices.PENDING,
                    adjustment_time=now_utc,
                    execution_status=ExecutionStatusChoices.PENDING,
                )
                adjusted += 1
                hit_written = True

            # 6. 标记已分时（不管竞价是否变化，只要在时段内就算分时）
            hit.is_time_pricing = TimePricingHitStatus.YES
            hit.save(update_fields=["is_time_pricing", "updated_at"])

        except Exception as e:
            err = f"campaign={hit.campaign_id} profile={hit.profile_id}: {e}"
            logger.error("[time_pricing_executor] %s", err, exc_info=True)
            errors.append(err)

    logger.info(
        "[time_pricing_executor] 完成 processed=%d adjusted=%d errors=%d",
        processed, adjusted, len(errors),
    )
    return {"processed": processed, "adjusted": adjusted, "errors": errors}
