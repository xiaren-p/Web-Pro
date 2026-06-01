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
from api_v2.services.ad_creation.ad_campaign_query_service import find_campaign_id_by_name
from api_v2.services.ad_creation.ad_lx_client import (
    LX_ADS_API_URL,
    build_lx_headers,
    parse_lx_result,
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
) -> tuple[str, str, str | None]:
    """向领星接口提交广告活动创建请求。

    result 列表中可能包含多个条目；若部分失败视为「异常」，全部失败视为「失败」。

    Args:
        queue (AdUploadQueue): 当前队列记录，持有 campaign_name / daily_budget 等字段。
        profile_id (int): 广告 Profile ID。
        targeting_type (str): "AUTO" 或 "MANUAL"。

    Returns:
        tuple[str, str, str | None]:
            - campaign_id: 成功/异常时从首个成功结果中提取的 campaignId；失败时为空字符串。
            - status: "SUCCESS" | "ANOMALY" | "FAILED"。
            - details: ANOMALY/FAILED 时的描述；SUCCESS 时为 None。
    """
    form_data = build_campaign_form_data(
        profile_id=profile_id,
        campaign_name=queue.campaign_name,
        targeting_type=targeting_type,
        daily_budget=float((queue.params or {}).get("daily_budget", 1.00)),
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
        return "", "FAILED", str(exc)

    status, details = parse_lx_result(resp_json)
    if status == "FAILED":
        # 广告活动名称已存在：通过查询接口反查已有活动的 campaignId，继续后续步骤。
        # 必须传入 profile_id 参数，防止跨 profile 误取同名活动。
        if details and "名称已存在" in details:
            logger.info(
                "[AdCampaignService] 广告活动名称已存在，尝试查询已有 campaignId: "
                "id=%s profile_id=%s name=%s",
                queue.pk,
                profile_id,
                queue.campaign_name,
            )
            found_id = find_campaign_id_by_name(profile_id, queue.campaign_name)
            if found_id:
                logger.info(
                    "[AdCampaignService] 反查成功，使用已有广告活动: id=%s campaignId=%s",
                    queue.pk,
                    found_id,
                )
                # 反查到已有 campaignId，立即落库到 step_ids。
                # 防止调度层回写前流程中断导致下次重试时重走创建逻辑。
                queue.step_ids = {**queue.step_ids, "campaign_id": found_id}
                queue.save(update_fields=["step_ids"])
                return found_id, "SUCCESS", None
            # 反查失败：返回明确错误，不以空字符串继续
            logger.error(
                "[AdCampaignService] 广告活动名称已存在且反查 campaignId 失败，"
                "需人工至领星后台查询后手动写入 step_ids: "
                "id=%s profile_id=%s name=%s",
                queue.pk,
                profile_id,
                queue.campaign_name,
            )
            return (
                "",
                "FAILED",
                f"广告活动「{queue.campaign_name}」已存在，但自动反查 campaignId 失败，"
                "请人工至领星后台查询广告活动 ID 后手动更新 step_ids[campaign_id]",
            )

        logger.warning(
            "[AdCampaignService] 广告活动创建失败: id=%s campaign=%s error=%s",
            queue.pk,
            queue.campaign_name,
            details,
        )
        return "", "FAILED", details

    # 从首个成功的 result 条目中提取 campaignId
    campaign_id = ""
    for item in (resp_json.get("result") or []):
        if item.get("code") == "SUCCESS" and item.get("campaignId"):
            campaign_id = str(item["campaignId"])
            break

    # 若响应标记为成功/异常但未能提取到 campaignId，必须拦截并返回失败。
    # 防止以空字符串写入 step_ids["campaign_id"]，导致重试时跳过检查失效后重复创建。
    if not campaign_id:
        logger.error(
            "[AdCampaignService] 广告活动接口成功但 campaignId 未提取到，"
            "需人工至领星后台确认广告活动是否已创建: id=%s name=%s resp=%s",
            queue.pk,
            queue.campaign_name,
            resp_json,
        )
        return (
            "",
            "FAILED",
            "广告活动在亚马逊侧可能已创建但 campaignId 提取失败，"
            "请人工至领星后台查询广告活动 ID 后手动更新 step_ids",
        )

    logger.info(
        "[AdCampaignService] 广告活动创建%s: id=%s campaignId=%s",
        "成功" if status == "SUCCESS" else "异常",
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
    return campaign_id, status, details
