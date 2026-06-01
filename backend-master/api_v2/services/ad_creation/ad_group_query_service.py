"""广告组查询服务（ad_group_query_service）。

职责：封装向领星 ad_group index 接口查询指定广告活动下广告组列表的逻辑，
用于在「广告组名称已存在」时通过名称反向查找 adGroupId，以继续后续步骤。
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from api_v2.services.ad_creation.ad_lx_client import build_lx_headers, write_request_log
from api_v2.models.api_request_log import ParamType

logger = logging.getLogger(__name__)

# 广告组列表查询接口（与创建接口不同，使用独立端点）
LX_AD_GROUP_INDEX_URL = "https://ads.lingxing.com/ad_report/ad_group/index/index"


def build_ad_group_query_headers(profile_id: int, campaign_id: str) -> dict[str, str]:
    """为广告组查询接口构造请求头。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 广告活动 ID。

    Returns:
        dict[str, str]: 请求头字典。
    """
    referer = (
        f"https://ads.lingxing.com/ad_report/ad_group/index/index"
        f"?profile_id={profile_id}&id={campaign_id}"
    )
    return build_lx_headers(
        profile_id=profile_id,
        page_name="/ad_report/ad_group/index/index",
        referer_path=referer,
    )


def build_ad_group_query_form_data(profile_id: int, campaign_id: str) -> dict[str, Any]:
    """构造广告组列表查询接口的 form-encoded 请求体。

    仅请求 name / ad_group_id 两个关键字段，减少无关数据传输。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 广告活动 ID（用于过滤该活动下的广告组）。

    Returns:
        dict[str, Any]: requests.post 的 data 参数字典。
    """
    return {
        "draw": "1",
        # 仅声明 name 列，其余通过 fields[] 补充
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
        "campaign_id": campaign_id,
        "fields[]": "name",
    }


def find_ad_group_id_by_name(
    profile_id: int,
    campaign_id: str,
    group_name: str,
) -> str | None:
    """通过广告组名称反查 adGroupId。

    向领星广告组列表接口查询指定广告活动下的所有广告组，
    以 group_name 精确匹配 data[].name 字段，返回对应的 ad_group_id。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 广告活动 ID。
        group_name (str): 目标广告组名称（精确匹配，如 "01/06/2026"）。

    Returns:
        str | None:
            - 匹配到时返回 adGroupId 字符串。
            - 未匹配到、请求失败或响应异常时返回 None。
    """
    headers = build_ad_group_query_headers(profile_id, campaign_id)
    form_data = build_ad_group_query_form_data(profile_id, campaign_id)

    logger.info(
        "[AdGroupQueryService] 查询广告组列表: profile_id=%s campaignId=%s name=%s",
        profile_id,
        campaign_id,
        group_name,
    )

    try:
        resp = requests.post(
            f"{LX_AD_GROUP_INDEX_URL}?ajax",
            data=form_data,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        resp_json: dict[str, Any] = resp.json()
    except requests.RequestException as exc:
        logger.error(
            "[AdGroupQueryService] HTTP 请求失败: profile_id=%s campaignId=%s err=%s",
            profile_id,
            campaign_id,
            exc,
            exc_info=True,
        )
        return None

    write_request_log(
        url=f"{LX_AD_GROUP_INDEX_URL}?ajax",
        headers=headers,
        params=form_data,
        response_body=resp_json,
        purpose=f"查询广告组列表（名称匹配）: campaignId={campaign_id} name={group_name}",
        param_type=ParamType.FORM,
    )

    if not resp_json.get("successful"):
        logger.warning(
            "[AdGroupQueryService] 接口返回 successful=false: profile_id=%s campaignId=%s resp=%s",
            profile_id,
            campaign_id,
            resp_json,
        )
        return None

    rows: list[dict] = resp_json.get("data") or []
    for row in rows:
        if row.get("name") == group_name and row.get("ad_group_id"):
            ad_group_id = str(row["ad_group_id"])
            logger.info(
                "[AdGroupQueryService] 匹配到广告组: name=%s ad_group_id=%s",
                group_name,
                ad_group_id,
            )
            return ad_group_id

    logger.warning(
        "[AdGroupQueryService] 未在列表中匹配到广告组名称: profile_id=%s campaignId=%s name=%s rows_count=%s",
        profile_id,
        campaign_id,
        group_name,
        len(rows),
    )
    return None
