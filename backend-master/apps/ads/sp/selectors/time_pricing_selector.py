"""SP 分时定价状态查询选择器。

提供分时生效状态检查与分时竞价展示映射构建。
``keyword_view`` 与 ``auto_targeting_view`` 共用此选择器。
"""
import logging
from typing import Any

from django.db.models import Max

from apps.ads.sp.timing.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from apps.ads.sp.rules.models.sp_bid_adjustment import SpBidAdjustment, ExecutionTypeChoices as BidExecType

logger = logging.getLogger(__name__)


def is_time_pricing_active(campaign_id: int, profile_id: int) -> bool:
    """检查指定广告活动是否正在分时生效中。

    is_time_pricing == 1(YES) 表示正在分时；0(NO) 表示分时结束。

    Args:
        campaign_id (int): 广告活动 ID。
        profile_id (int): 店铺 Profile ID。

    Returns:
        bool: 正在分时返回 True。
    """
    return AdTimePricingHit.objects.filter(
        campaign_id=campaign_id,
        profile_id=profile_id,
        is_time_pricing=TimePricingHitStatus.YES,
    ).exists()


def build_time_pricing_bid_map(
    entity_ids: list[str],
    entity_field: str,
    campaign_id: int,
    profile_id: int,
    currency_icon: str,
) -> dict[str, str]:
    """构建分时竞价展示映射：分时生效中时显示最近一次 TIME_PRICING_START 的 bid_after，否则 "-"。

    Args:
        entity_ids: 实体 ID 列表。
        entity_field: "keyword_id" 或 "target_id"。
        campaign_id: 广告活动 ID。
        profile_id: 店铺 Profile ID。
        currency_icon: 货币符号。

    Returns:
        dict[str, str]: 实体 ID → 展示字符串（如 "$0.50" 或 "-"）。
    """
    if not AdTimePricingHit.objects.filter(
        campaign_id=campaign_id, profile_id=profile_id,
        is_time_pricing=TimePricingHitStatus.YES,
    ).exists():
        return {k: "-" for k in entity_ids}

    int_ids = [int(x) for x in entity_ids if x]
    if not int_ids:
        return {}

    latest = (
        SpBidAdjustment.objects
        .filter(
            **{f"{entity_field}__in": int_ids},
            execution_type=BidExecType.TIME_PRICING_START,
            campaign_id=campaign_id,
            profile_id=profile_id,
        )
        .values(entity_field)
        .annotate(max_id=Max("id"))
    )
    id_map = {row[entity_field]: row["max_id"] for row in latest if row["max_id"]}
    if not id_map:
        return {k: "-" for k in entity_ids}

    records = SpBidAdjustment.objects.filter(id__in=list(id_map.values())).only(
        entity_field, "bid_after",
    )
    rec_map = {getattr(r, entity_field): r for r in records if getattr(r, entity_field)}

    result: dict[str, str] = {}
    for kid in entity_ids:
        kid_int = int(kid)
        rec = rec_map.get(kid_int)
        if rec and rec.bid_after is not None:
            result[kid] = f"{currency_icon}{float(rec.bid_after):.2f}"
        else:
            result[kid] = "-"
    return result
