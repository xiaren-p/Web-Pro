"""广告组创建服务（ad_group_service）。

职责：封装向领星 post_adGroups 接口提交创建广告组的完整逻辑，
AUTO 广告同步提交四种自动定向竞价目标（auto_targets）。
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
    parse_lx_result,
    write_request_log,
)

logger = logging.getLogger(__name__)


def build_ad_group_form_data(
    profile_id: int,
    campaign_id: str,
    targeting_type: str,
    default_bid: float,
    close_match_bid: float,
    loose_match_bid: float,
    substitutes_bid: float,
    complements_bid: float,
) -> dict[str, Any]:
    """构造广告组创建接口的 form-encoded 请求体。

    广告组名称固定为当天日期（格式 DD/MM/YYYY）。
    AUTO 广告额外附加四种自动定向目标（auto_targets）及各自竞价。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 第一步创建广告活动后返回的 campaignId。
        targeting_type (str): "AUTO" 或 "MANUAL"。
        default_bid (float): 广告组默认竞价。
        close_match_bid (float): 紧密匹配（queryHighRelMatches）竞价，AUTO 专用。
        loose_match_bid (float): 同类匹配（queryBroadRelMatches）竞价，AUTO 专用。
        substitutes_bid (float): 宽泛匹配（asinSubstituteRelated）竞价，AUTO 专用。
        complements_bid (float): 关联匹配（asinAccessoryRelated）竞价，AUTO 专用。

    Returns:
        dict[str, Any]: requests.post 的 data 参数字典。
    """
    group_name = date.today().strftime("%d/%m/%Y")

    # 基础字段：AUTO 与 MANUAL 相同，均须包含以下字段
    data: dict[str, Any] = {
        "profile_id": profile_id,
        "api_method": "post_adGroups",
        "ad_type": "sp",
        "api_version": "v3",
        "params[adGroups][0][state]": "enabled",
        "params[adGroups][0][defaultBid]": default_bid,
        "params[adGroups][0][name]": group_name,
        "params[adGroups][0][campaignId]": campaign_id,
    }

    if targeting_type == "AUTO":
        # AUTO 额外附加四种自动定向目标竞价
        auto_targets: list[tuple[str, Any]] = [
            ("auto_targets[0][expression][0][type]", "queryHighRelMatches"),
            ("auto_targets[0][state]", "enabled"),
            ("auto_targets[0][bid]", close_match_bid),
            ("auto_targets[1][expression][0][type]", "queryBroadRelMatches"),
            ("auto_targets[1][state]", "enabled"),
            ("auto_targets[1][bid]", loose_match_bid),
            ("auto_targets[2][expression][0][type]", "asinSubstituteRelated"),
            ("auto_targets[2][state]", "enabled"),
            ("auto_targets[2][bid]", substitutes_bid),
            ("auto_targets[3][expression][0][type]", "asinAccessoryRelated"),
            ("auto_targets[3][state]", "enabled"),
            ("auto_targets[3][bid]", complements_bid),
        ]
        for key, value in auto_targets:
            data[key] = value
    # MANUAL：仅基础字段，无需附加定向参数；关键词由后续 post_keywords 单独提交

    return data


def build_ad_group_headers(
    profile_id: int,
    campaign_id: str,
    targeting_type: str,
) -> dict[str, str]:
    """为广告组创建请求构造请求头，覆盖页面名和 referer。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 广告活动 ID。
        targeting_type (str): "AUTO" 或 "MANUAL"。

    Returns:
        dict[str, str]: 修改后的请求头字典。
    """
    type_param = "auto" if targeting_type == "AUTO" else "manual"
    referer = (
        f"https://ads.lingxing.com/ad_report/campaign/generate/gen_ad_group"
        f"?profile_id={profile_id}&campaignId={campaign_id}&type={type_param}"
    )
    return build_lx_headers(
        profile_id=profile_id,
        page_name="/ad_report/campaign/generate/gen_ad_group",
        referer_path=referer,
    )


def create_ad_group(
    queue: AdUploadQueue,
    profile_id: int,
    campaign_id: str,
    targeting_type: str,
) -> tuple[str, str, str | None]:
    """向领星接口提交广告组创建请求。

    AUTO 广告同步提交四个 auto_targets（紧密匹配、同类匹配、宽泛匹配、关联匹配）。
    result 列表中可能包含多个条目（adGroup + 各 auto_target）；
    部分失败视为「异常」，全部失败视为「失败」，均不影响 adGroupId 提取。
    广告组名称自动取当天日期（DD/MM/YYYY）。

    Args:
        queue (AdUploadQueue): 当前队列记录，持有各竞价字段。
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 第一步创建广告活动后返回的 campaignId。
        targeting_type (str): "AUTO" 或 "MANUAL"。

    Returns:
        tuple[str, str, str | None]:
            - ad_group_id: 成功/异常时从首个成功结果中提取的 adGroupId；失败时为空字符串。
            - status: "SUCCESS" | "ANOMALY" | "FAILED"。
            - details: ANOMALY/FAILED 时的描述；SUCCESS 时为 None。
    """
    _p = queue.params or {}
    form_data = build_ad_group_form_data(
        profile_id=profile_id,
        campaign_id=campaign_id,
        targeting_type=targeting_type,
        default_bid=float(_p.get("default_bid", 0.12)),
        close_match_bid=float(_p.get("close_match_bid", 0.12)),
        loose_match_bid=float(_p.get("loose_match_bid", 0.10)),
        substitutes_bid=float(_p.get("substitutes_bid", 0.10)),
        complements_bid=float(_p.get("complements_bid", 0.10)),
    )
    headers = build_ad_group_headers(profile_id, campaign_id, targeting_type)

    logger.info(
        "[AdGroupService] 创建广告组: id=%s campaignId=%s targeting=%s",
        queue.pk,
        campaign_id,
        targeting_type,
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
            "[AdGroupService] HTTP 请求失败: id=%s campaignId=%s err=%s",
            queue.pk,
            campaign_id,
            exc,
            exc_info=True,
        )
        return "", "FAILED", str(exc)

    status, details = parse_lx_result(resp_json)
    if status == "FAILED":
        logger.warning(
            "[AdGroupService] 广告组创建失败: id=%s campaignId=%s error=%s",
            queue.pk,
            campaign_id,
            details,
        )
        return "", "FAILED", details

    # 从首个成功的 result 条目中提取 adGroupId
    ad_group_id = ""
    for item in (resp_json.get("result") or []):
        if item.get("code") == "SUCCESS" and item.get("adGroupId"):
            ad_group_id = str(item["adGroupId"])
            break

    logger.info(
        "[AdGroupService] 广告组创建%s: id=%s campaignId=%s adGroupId=%s",
        "成功" if status == "SUCCESS" else "异常",
        queue.pk,
        campaign_id,
        ad_group_id,
    )
    write_request_log(
        url=LX_ADS_API_URL,
        headers=headers,
        params=form_data,
        response_body=resp_json,
        purpose=f"创建广告组: campaignId={campaign_id} targeting={targeting_type}",
    )
    return ad_group_id, status, details
