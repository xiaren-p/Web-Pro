"""广告活动创建服务（ad_campaign_service）。

职责：封装向领星 post_campaigns 接口提交创建广告活动的完整逻辑，
包括请求体构造、发起 HTTP 请求、解析响应并返回 campaignId。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import requests

from api_v2.models.ad_upload_queue import AdUploadQueue
from api_v2.services.ad_creation.ad_lx_client import (
    LX_ADS_API_URL,
    build_lx_headers,
    parse_lx_result_error,
    write_request_log,
)

logger = logging.getLogger(__name__)


def build_campaign_form_data(
    profile_id: int,
    campaign_name: str,
    targeting_type: str,
    daily_budget: float,
) -> dict[str, Any]:
    """构造广告活动创建接口的 form-encoded 请求体。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_name (str): 广告活动名称（含 AUTO/MANU 后缀）。
        targeting_type (str): "AUTO" 或 "MANUAL"。
        daily_budget (float): 每日预算。

    Returns:
        dict[str, Any]: requests.post 的 data 参数字典。
    """
    today = date.today().isoformat()
    return {
        "profile_id": profile_id,
        "api_method": "post_campaigns",
        "params[campaigns][0][state]": "ENABLED",
        "params[campaigns][0][name]": campaign_name,
        "params[campaigns][0][targetingType]": targeting_type,
        "params[campaigns][0][startDate]": today,
        "params[campaigns][0][endDate]": "",
        "params[campaigns][0][budget][budgetType]": "DAILY",
        "params[campaigns][0][budget][budget]": daily_budget,
        "params[campaigns][0][dynamicBidding][strategy]": "MANUAL",
        "params[campaigns][0][dynamicBidding][placementBidding][0][placement]": "PLACEMENT_TOP",
        "params[campaigns][0][dynamicBidding][placementBidding][0][percentage]": 0,
        "params[campaigns][0][dynamicBidding][placementBidding][1][placement]": "PLACEMENT_REST_OF_SEARCH",
        "params[campaigns][0][dynamicBidding][placementBidding][1][percentage]": 0,
        "params[campaigns][0][dynamicBidding][placementBidding][2][placement]": "PLACEMENT_PRODUCT_PAGE",
        "params[campaigns][0][dynamicBidding][placementBidding][2][percentage]": 0,
        "params[campaigns][0][dynamicBidding][placementBidding][3][placement]": "SITE_AMAZON_BUSINESS",
        "params[campaigns][0][dynamicBidding][placementBidding][3][percentage]": 0,
        "ad_type": "sp",
        "api_version": "v3",
    }


def create_campaign(
    queue: AdUploadQueue,
    profile_id: int,
    targeting_type: str,
) -> tuple[str, str | None]:
    """向领星接口提交广告活动创建请求。

    Args:
        queue (AdUploadQueue): 当前队列记录，持有 campaign_name / daily_budget 等字段。
        profile_id (int): 广告 Profile ID。
        targeting_type (str): "AUTO" 或 "MANUAL"。

    Returns:
        tuple[str, str | None]:
            - campaign_id: 成功时为接口返回的 campaignId，失败时为空字符串。
            - error_msg: 失败时为错误描述；成功时为 None。
    """
    form_data = build_campaign_form_data(
        profile_id=profile_id,
        campaign_name=queue.campaign_name,
        targeting_type=targeting_type,
        daily_budget=float(queue.daily_budget),
    )
    headers = build_lx_headers(profile_id)

    logger.info(
        "[AdCampaignService] 创建广告活动: id=%s campaign=%s profile=%s",
        queue.pk,
        queue.campaign_name,
        profile_id,
    )

    try:
        resp = requests.post(
            LX_ADS_API_URL,
            data=form_data,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        resp_json: dict[str, Any] = resp.json()
    except requests.RequestException as exc:
        logger.error(
            "[AdCampaignService] HTTP 请求失败: id=%s campaign=%s err=%s",
            queue.pk,
            queue.campaign_name,
            exc,
            exc_info=True,
        )
        return "", str(exc)

    error_msg = parse_lx_result_error(resp_json)
    if error_msg is not None:
        logger.warning(
            "[AdCampaignService] 广告活动创建失败: id=%s campaign=%s error=%s",
            queue.pk,
            queue.campaign_name,
            error_msg,
        )
        return "", error_msg

    result_items: list[dict[str, Any]] = resp_json.get("result") or []
    campaign_id: str = result_items[0].get("campaignId", "") if result_items else ""
    logger.info(
        "[AdCampaignService] 广告活动创建成功: id=%s campaignId=%s",
        queue.pk,
        campaign_id,
    )
    write_request_log(
        url=LX_ADS_API_URL,
        headers=headers,
        params=form_data,
        response_body=resp_json,
        purpose=f"创建广告活动: {queue.campaign_name}",
    )
    return campaign_id, None
