"""广告活动查询服务（ad_campaign_query_service）。

职责：封装向领星广告活动列表接口查询指定名称的广告活动 ID 的逻辑，
用于在「广告活动名称已存在」时通过名称 + profile_id 反向查找 campaignId，
以便继续后续步骤而无需人工介入。
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from api_v2.services.ad_creation.ad_lx_client import build_lx_headers, write_request_log
from api_v2.models.api_request_log import ParamType

logger = logging.getLogger(__name__)

# 广告活动列表查询接口（跨 profile 搜索，须在 data[] 中再次按 profile_id 过滤）
LX_CAMPAIGN_INDEX_URL = "https://ads.lingxing.com/ad_report/profile/campaign/index"


def build_campaign_query_headers(profile_id: int) -> dict[str, str]:
    """为广告活动查询接口构造请求头。

    Args:
        profile_id (int): 广告 Profile ID（用于构造 referer）。

    Returns:
        dict[str, str]: 请求头字典。
    """
    referer = (
        f"https://ads.lingxing.com/ad_report/profile/campaign/index"
        f"?profile_id={profile_id}"
    )
    return build_lx_headers(
        profile_id=profile_id,
        page_name="/ad_report/profile/campaign/index",
        referer_path=referer,
    )


def build_campaign_query_form_data(
    profile_id: int,
    campaign_name: str,
) -> dict[str, Any]:
    """构造广告活动列表查询接口的 form-encoded 请求体。

    使用 search_type=campaign_name + name 过滤，仅请求 name / campaign_id 字段，
    减少无关数据传输。接口会跨所有 profile 返回同名活动，须在返回值中再次按
    profile_id 精确匹配。

    Args:
        profile_id (int): 广告 Profile ID（接口必须传参，同时用于匹配返回数据）。
        campaign_name (str): 目标广告活动名称（精确匹配）。

    Returns:
        dict[str, Any]: requests.post 的 data 参数字典。
    """
    return {
        "draw": "1",
        "columns[0][data]": "name",
        "columns[0][name]": "",
        "columns[0][searchable]": "true",
        "columns[0][orderable]": "false",
        "columns[0][search][value]": "",
        "columns[0][search][regex]": "false",
        "order[0][column]": "0",
        "order[0][dir]": "asc",
        "start": "0",
        "length": "50",
        "search[value]": "",
        "search[regex]": "false",
        "profile_id": profile_id,
        "search_type": "campaign_name",
        "name": campaign_name,
        "fields[]": "name",
    }


def find_campaign_id_by_name(
    profile_id: int,
    campaign_name: str,
) -> str | None:
    """通过广告活动名称 + profile_id 反查 campaignId。

    向领星广告活动列表接口查询指定名称的广告活动，
    以 campaign_name 精确匹配 data[].name 且 data[].profile_id == profile_id
    的条目，返回对应的 campaign_id。

    由于同一名称可能在不同 profile 下各存在一条记录，必须同时校验 profile_id，
    避免跨 profile 误取。

    Args:
        profile_id (int): 广告 Profile ID（必须与目标活动所属 profile 一致）。
        campaign_name (str): 目标广告活动名称（精确匹配）。

    Returns:
        str | None:
            - 匹配到时返回 campaignId 字符串。
            - 未匹配到、请求失败或响应异常时返回 None。
    """
    headers = build_campaign_query_headers(profile_id)
    form_data = build_campaign_query_form_data(profile_id, campaign_name)

    logger.info(
        "[AdCampaignQueryService] 查询广告活动列表: profile_id=%s name=%s",
        profile_id,
        campaign_name,
    )

    try:
        resp = requests.post(
            f"{LX_CAMPAIGN_INDEX_URL}?ajax",
            data=form_data,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        resp_json: dict[str, Any] = resp.json()
    except requests.RequestException as exc:
        logger.error(
            "[AdCampaignQueryService] HTTP 请求失败: profile_id=%s name=%s err=%s",
            profile_id,
            campaign_name,
            exc,
            exc_info=True,
        )
        return None

    write_request_log(
        url=f"{LX_CAMPAIGN_INDEX_URL}?ajax",
        headers=headers,
        params=form_data,
        response_body=resp_json,
        purpose=f"查询广告活动列表（名称匹配）: profile_id={profile_id} name={campaign_name}",
        param_type=ParamType.FORM,
    )

    if not resp_json.get("successful"):
        logger.warning(
            "[AdCampaignQueryService] 接口返回 successful=false: profile_id=%s name=%s resp=%s",
            profile_id,
            campaign_name,
            resp_json,
        )
        return None

    rows: list[dict] = resp_json.get("data") or []
    profile_id_str = str(profile_id)
    for row in rows:
        # 必须同时匹配 name 和 profile_id，防止跨 profile 误取同名活动
        if (
            row.get("name") == campaign_name
            and str(row.get("profile_id") or "") == profile_id_str
            and row.get("campaign_id")
        ):
            campaign_id = str(row["campaign_id"])
            logger.info(
                "[AdCampaignQueryService] 匹配到广告活动: name=%s profile_id=%s campaign_id=%s",
                campaign_name,
                profile_id,
                campaign_id,
            )
            return campaign_id

    logger.warning(
        "[AdCampaignQueryService] 未在列表中匹配到广告活动: profile_id=%s name=%s rows_count=%s",
        profile_id,
        campaign_name,
        len(rows),
    )
    return None
