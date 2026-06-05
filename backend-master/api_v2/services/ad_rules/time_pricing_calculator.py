"""分时竞价计算与写入工具（time_pricing_calculator）。

提供分时开始竞价计算、回调竞价计算、投放项实时查询和批量写入的通用逻辑。

输入：timeline 命中记录 + 策略
输出：SpBidAdjustment 调整记录列表 + AdTimePricingHit 的待更新标记

注意：投放项改为每条 hit 实时 SQL 查询（fetch_ad_items），不再全表扫内存。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api_v1.models.lingxing.ads.basic.lx_sp_keyword import LxSpKeyword
from api_v1.models.lingxing.ads.basic.lx_sp_target import LxSpTarget
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices, ExecutionStatusChoices, ExecutionTypeChoices, SpBidAdjustment,
)

logger = logging.getLogger(__name__)


# ============================================================
# 竞价规则计算
# ============================================================

def calc_new_bid(current_bid: float, rule: dict) -> float | None:
    """根据单条规则计算调整后的竞价。

    Args:
        current_bid: 当前竞价
        rule: {"operateType", "operateValue", "limitValue", "triggerValue", "targetValue"}

    Returns:
        调整后竞价；bid_above/below 条件不满足时返回 None（不调整）
    """
    op = rule.get("operateType", "")
    val = float(rule.get("operateValue", 0) or 0)
    lim = float(rule.get("limitValue", 0) or 0)
    trig = float(rule.get("triggerValue", 0) or 0)
    tgt = float(rule.get("targetValue", 0) or 0)

    if op == "percent_decrease":
        return max(current_bid * (1 - val / 100), lim) if val else current_bid
    if op == "percent_increase":
        return min(current_bid * (1 + val / 100), lim) if val else current_bid
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


def calc_callback_bid(current_bid: float, callback_settings: dict) -> float | None:
    """根据回调策略计算恢复后的竞价。

    Args:
        current_bid: 投放项的当前竞价
        callback_settings: strategy.callback_settings

    Returns:
        回调后竞价；type=none 时返回 None
    """
    cb_type = callback_settings.get("type", "none")
    if cb_type == "multiplier":
        mul = float(callback_settings.get("multiplier", 1.0) or 1.0)
        return current_bid * mul
    if cb_type == "fixed":
        return float(callback_settings.get("fixed", current_bid) or current_bid)
    if cb_type == "previous":
        return current_bid
    return None


# ============================================================
# 投放项查询
# ============================================================

def fetch_ad_items(
    campaign_id: int,
    profile_id: int,
    targeting_type: str,
) -> list[dict[str, Any]]:
    """按广告活动和店铺实时查询投放项，不预加载全表。

    Args:
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID
        targeting_type: 投放类型（auto=定位组, manual=关键词）

    Returns:
        [{"item_type": "target"/"keyword", "item_id": int, "ad_group_id": int, "bid": float}]
    """
    items: list[dict[str, Any]] = []

    if targeting_type in ("auto", ""):
        items.extend({
            "item_type": "target",
            "item_id": t.target_id,
            "ad_group_id": t.ad_group_id,
            "bid": float(t.bid),
        } for t in LxSpTarget.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
            bid__isnull=False,
            state="enabled",
        ).iterator())

    if targeting_type in ("manual", ""):
        items.extend({
            "item_type": "keyword",
            "item_id": k.keyword_id,
            "ad_group_id": k.ad_group_id,
            "bid": float(k.bid),
        } for k in LxSpKeyword.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
            bid__isnull=False,
            state="enabled",
        ).iterator())

    return items


# ============================================================
# 写入工具
# ============================================================

def append_start_adjustment(
    item: dict[str, Any],
    campaign_id: int,
    profile_id: int,
    strategy_id: int,
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
) -> bool:
    """将单条投放项的竞价调整添加到收集列表。

    若 bid_after == bid（竞价不变），直接标 SUCCESS 不调 API。

    Args:
        item: {"item_type", "item_id", "bid", "bid_after"} 投放项数据
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID
        strategy_id: 命中策略 ID
        now_utc: 调整时间
        adjustments: 待批量写入的列表（引用传递）

    Returns:
        True 表示需要调 API，False 表示竞价不变直接标记成功
    """
    is_target = item["item_type"] == "target"
    bid_before = item.get("bid_before", item["bid"])
    bid_after = item.get("bid_after", item["bid"])

    if bid_before == bid_after:
        adjustments.append(SpBidAdjustment(
            target_id=item["item_id"] if is_target else None,
            keyword_id=item["item_id"] if not is_target else None,
            campaign_id=campaign_id,
            profile_id=profile_id,
            execution_type=ExecutionTypeChoices.TIME_PRICING_START,
            time_pricing_rule_id=strategy_id,
            auto_rule_id=None,
            is_time_pricing=TimePricingHitStatus.YES,
            bid_before=bid_before,
            bid_after=bid_after,
            adjustment_status=AdjustmentStatusChoices.SUCCESS,
            adjustment_time=now_utc,
            execution_status=ExecutionStatusChoices.SUCCESS,
            msg="分时竞价前与竞价后竞价相等，无需调整",
        ))
        return False

    adjustments.append(SpBidAdjustment(
        target_id=item["item_id"] if is_target else None,
        keyword_id=item["item_id"] if not is_target else None,
        campaign_id=campaign_id,
        profile_id=profile_id,
        execution_type=ExecutionTypeChoices.TIME_PRICING_START,
        time_pricing_rule_id=strategy_id,
        auto_rule_id=None,
        is_time_pricing=TimePricingHitStatus.YES,
        bid_before=bid_before,
        bid_after=bid_after,
        adjustment_status=AdjustmentStatusChoices.PENDING,
        adjustment_time=now_utc,
        execution_status=ExecutionStatusChoices.PENDING,
    ))
    return True


def append_callback_adjustment(
    item: dict[str, Any],
    callback_bid: float,
    campaign_id: int,
    profile_id: int,
    strategy_id: int,
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
) -> bool:
    """将单条投放项的回调竞价调整添加到收集列表。

    回调竞价 == 原始竞价（bid_before）时跳过不写。
    原始竞价在 _do_start 中保存为 item["bid_before"]。

    Args:
        item: {"item_type", "item_id", "bid", "bid_before"} 投放项数据
        callback_bid: 回调策略计算出的目标竞价
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID
        strategy_id: 命中策略 ID
        now_utc: 调整时间
        adjustments: 待批量写入的列表（引用传递）

    Returns:
        True 表示写了记录，False 表示竞价相等跳过
    """
    original_bid = item.get("bid_before", item["bid"])
    if round(callback_bid, 4) == round(original_bid, 4):
        return False

    is_target = item["item_type"] == "target"
    adjustments.append(SpBidAdjustment(
        target_id=item["item_id"] if is_target else None,
        keyword_id=item["item_id"] if not is_target else None,
        campaign_id=campaign_id,
        profile_id=profile_id,
        execution_type=ExecutionTypeChoices.TIME_PRICING_CALLBACK,
        time_pricing_rule_id=strategy_id,
        auto_rule_id=None,
        is_time_pricing=TimePricingHitStatus.NO,
        bid_before=None,
        bid_after=callback_bid,
        adjustment_status=AdjustmentStatusChoices.PENDING,
        adjustment_time=now_utc,
        execution_status=ExecutionStatusChoices.PENDING,
    ))
    return True


def write_batch(
    adjustments: list[SpBidAdjustment],
    hits_to_update: list[AdTimePricingHit],
) -> None:
    """批量写入调整记录和命中状态。

    Args:
        adjustments: 待写入的 SpBidAdjustment 列表
        hits_to_update: 待更新 is_time_pricing/is_callback 的记录列表
    """
    if adjustments:
        SpBidAdjustment.objects.bulk_create(adjustments, batch_size=500)
    if hits_to_update:
        AdTimePricingHit.objects.bulk_update(
            hits_to_update,
            ["is_time_pricing", "is_callback", "rule_updated_today", "updated_at"],
            batch_size=500,
        )
