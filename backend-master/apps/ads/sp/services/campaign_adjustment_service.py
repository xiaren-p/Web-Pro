"""SP 广告活动调整业务服务。

封装广告活动预算调整、状态调整（含批量操作）的事务写入逻辑。
供 ``ad_campaign_view``、``keyword_view``、``auto_targeting_view`` 共用。
"""
import logging
from datetime import datetime
from typing import Any

from rest_framework.request import Request

from apps.ads.sp.models.lx_sp_campaign import LxSpCampaign
from apps.ads.sp.models.lx_sp_keyword import LxSpKeyword
from apps.ads.sp.models.lx_sp_target import LxSpTarget
from apps.ads.sp.rules.models.sp_campaign_adjustment import (
    SpCampaignAdjustment,
    CampaignExecutionTypeChoices,
)
from apps.ads.sp.rules.models.sp_bid_adjustment import (
    SpBidAdjustment,
    ExecutionTypeChoices,
    ExecutionStatusChoices,
)
from apps.ads.views._helpers import get_operator_name
from apps.common.utils.responses import drf_error, drf_ok

logger = logging.getLogger(__name__)


def adjust_campaign_budget(request: Request) -> dict:
    """单个广告活动预算调整。

    写入 SpCampaignAdjustment 记录，更新 LxSpCampaign.daily_budget。

    Args:
        request: DRF 请求对象，body 需含 campaign_id/profile_id/daily_budget。

    Returns:
        dict: ``{ok: True}`` 成功；``{error: str, status: int}`` 失败。
    """
    data = request.data or {}
    campaign_id = data.get("campaign_id")
    profile_id = data.get("profile_id")
    daily_budget = data.get("daily_budget")

    if not campaign_id or not profile_id or daily_budget is None:
        return {"error": "缺少必填字段", "status": 400}

    try:
        campaign = LxSpCampaign.objects.get(campaign_id=campaign_id, profile_id=profile_id)
    except LxSpCampaign.DoesNotExist:
        return {"error": "广告活动不存在", "status": 404}

    old_budget = campaign.daily_budget
    campaign.daily_budget = float(daily_budget)
    campaign.save(update_fields=["daily_budget"])

    SpCampaignAdjustment.objects.create(
        campaign_id=campaign_id,
        profile_id=profile_id,
        execution_type=CampaignExecutionTypeChoices.MANUAL_BUDGET_ADJUSTMENT,
        daily_budget_before=old_budget,
        daily_budget_after=float(daily_budget),
        operator=get_operator_name(request),
    )

    return {"ok": True}


def adjust_campaign_state(request: Request) -> dict:
    """单个广告活动状态变更（启用/暂停）。

    写入 SpCampaignAdjustment 记录，更新 LxSpCampaign.state。

    Args:
        request: DRF 请求对象，body 需含 campaign_id/profile_id/state。

    Returns:
        dict: ``{ok: True}`` 成功；``{error: str, status: int}`` 失败。
    """
    data = request.data or {}
    campaign_id = data.get("campaign_id")
    profile_id = data.get("profile_id")
    state = data.get("state")

    if not campaign_id or not profile_id or state is None:
        return {"error": "缺少必填字段", "status": 400}

    try:
        campaign = LxSpCampaign.objects.get(campaign_id=campaign_id, profile_id=profile_id)
    except LxSpCampaign.DoesNotExist:
        return {"error": "广告活动不存在", "status": 404}

    exec_type = CampaignExecutionTypeChoices.CAMPAIGN_ENABLE if state else CampaignExecutionTypeChoices.CAMPAIGN_PAUSE

    campaign.state = state
    campaign.save(update_fields=["state"])

    SpCampaignAdjustment.objects.create(
        campaign_id=campaign_id,
        profile_id=profile_id,
        execution_type=exec_type,
        state_before=not state,
        state_after=state,
        operator=get_operator_name(request),
    )

    return {"ok": True}


def batch_adjust_campaign_state(request: Request) -> dict:
    """批量广告活动状态变更。

    一次请求批量写入 SpCampaignAdjustment + 更新 LxSpCampaign.state。

    Args:
        request: DRF 请求对象，body 需含 items (list[dict])。

    Returns:
        dict: ``{ok: True}`` 成功；``{error: str, status: int}`` 失败。
    """
    items = request.data.get("items", [])

    if not items:
        return {"error": "缺少 items 参数", "status": 400}

    adjustments = []
    campaigns_to_update = []

    for item in items:
        campaign_id = item.get("campaign_id")
        profile_id = item.get("profile_id")
        state = item.get("state")

        if not all([campaign_id, profile_id]):
            continue

        campaign = LxSpCampaign.objects.filter(campaign_id=campaign_id, profile_id=profile_id).first()
        if not campaign:
            continue

        exec_type = CampaignExecutionTypeChoices.CAMPAIGN_ENABLE if state else CampaignExecutionTypeChoices.CAMPAIGN_PAUSE
        campaign.state = state
        campaigns_to_update.append(campaign)

        adjustments.append(SpCampaignAdjustment(
            campaign_id=campaign_id,
            profile_id=profile_id,
            execution_type=exec_type,
            state_before=not state,
            state_after=state,
            operator=get_operator_name(request),
        ))

    if campaigns_to_update:
        LxSpCampaign.objects.bulk_update(campaigns_to_update, ["state"])
    if adjustments:
        SpCampaignAdjustment.objects.bulk_create(adjustments)

    return {"ok": True}


def batch_adjust_campaign_budget(request: Request) -> dict:
    """批量广告活动预算调整。

    一次请求批量写入 SpCampaignAdjustment + 更新 LxSpCampaign.daily_budget。

    Args:
        request: DRF 请求对象，body 需含 items (list[dict])。

    Returns:
        dict: ``{ok: True}`` 成功；``{error: str, status: int}`` 失败。
    """
    items = request.data.get("items", [])

    if not items:
        return {"error": "缺少 items 参数", "status": 400}

    adjustments = []
    campaigns_to_update = []

    for item in items:
        campaign_id = item.get("campaign_id")
        profile_id = item.get("profile_id")
        daily_budget = item.get("daily_budget")

        if not all([campaign_id, profile_id]) or daily_budget is None:
            continue

        campaign = LxSpCampaign.objects.filter(campaign_id=campaign_id, profile_id=profile_id).first()
        if not campaign:
            continue

        old_budget = campaign.daily_budget
        campaign.daily_budget = float(daily_budget)
        campaigns_to_update.append(campaign)

        adjustments.append(SpCampaignAdjustment(
            campaign_id=campaign_id,
            profile_id=profile_id,
            execution_type=CampaignExecutionTypeChoices.MANUAL_BUDGET_ADJUSTMENT,
            daily_budget_before=old_budget,
            daily_budget_after=float(daily_budget),
            operator=get_operator_name(request),
        ))

    if campaigns_to_update:
        LxSpCampaign.objects.bulk_update(campaigns_to_update, ["daily_budget"])
    if adjustments:
        SpCampaignAdjustment.objects.bulk_create(adjustments)

    return {"ok": True}
