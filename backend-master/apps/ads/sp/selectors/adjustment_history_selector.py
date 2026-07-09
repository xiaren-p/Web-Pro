"""投放实体调整历史查询 selector。
按 keyword_id / target_id 查询 SpBidAdjustment 完整调整记录，
包含自动规则、手动调整、分时调价、暂停/启用 所有类型。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.db.models import Q

from apps.ads.sp.rules.models.sp_bid_adjustment import SpBidAdjustment
from apps.ads.sp.rules.models.sp_campaign_adjustment import SpCampaignAdjustment


def query_entity_adjustment_history(
    entity_type: str,
    entity_id: int,
    profile_id: int,
    days: int = 90,
) -> list[dict[str, Any]]:
    """查询投放实体（关键词/定位组/商品投放）的调整历史。

    Args:
        entity_type: "keyword" | "target"
        entity_id: 实体 ID
        profile_id: 店铺 ID
        days: 向前查询天数，默认 90 天

    Returns:
        [{adjustment_time, execution_type, bid_before, bid_after,
          operator, msg, adjustment_status, execution_status,
          auto_rule_id, time_pricing_rule_id}]
    """
    date_start = datetime.now() - timedelta(days=days)
    filter_kwargs = {"profile_id": profile_id, "adjustment_time__gte": date_start}
    if entity_type == "keyword":
        filter_kwargs["keyword_id"] = entity_id
    else:
        filter_kwargs["target_id"] = entity_id

    records = SpBidAdjustment.objects.filter(
        **filter_kwargs,
    ).order_by("-adjustment_time")

    return [
        {
            "adjustment_time": r.adjustment_time,
            "execution_type": r.execution_type,
            "bid_before": float(r.bid_before) if r.bid_before is not None else None,
            "bid_after": float(r.bid_after) if r.bid_after is not None else None,
            "operator": r.operator or "",
            "msg": r.msg or "",
            "adjustment_status": r.adjustment_status,
            "execution_status": r.execution_status,
            "auto_rule_id": r.auto_rule_id,
            "time_pricing_rule_id": r.time_pricing_rule_id,
        }
        for r in records
    ]


def query_campaign_adjustment_history(
    campaign_id: int,
    profile_id: int,
    days: int = 90,
) -> list[dict[str, Any]]:
    """查询广告活动预算/暂停/启用的调整历史。

    Args:
        campaign_id: 广告活动 ID
        profile_id: 店铺 ID
        days: 向前查询天数，默认 90 天

    Returns:
        [{adjustment_time, execution_type, budget_before, budget_after,
          operator, msg, adjustment_status, execution_status}]
    """
    date_start = datetime.now() - timedelta(days=days)
    records = SpCampaignAdjustment.objects.filter(
        campaign_id=campaign_id,
        profile_id=profile_id,
        adjustment_time__gte=date_start,
    ).order_by("-adjustment_time")

    return [
        {
            "adjustment_time": r.adjustment_time,
            "execution_type": r.execution_type,
            "budget_before": float(r.budget_before) if r.budget_before is not None else None,
            "budget_after": float(r.budget_after) if r.budget_after is not None else None,
            "operator": r.operator or "",
            "msg": r.msg or "",
            "adjustment_status": r.adjustment_status,
            "execution_status": r.execution_status,
            "auto_rule_id": r.auto_rule_id,
        }
        for r in records
    ]
