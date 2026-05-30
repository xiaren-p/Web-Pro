"""关键词创建服务（ad_keyword_service）。

职责：封装向领星 post_keywords 接口批量提交 MANUAL 广告关键词的完整逻辑。
与其他步骤的差异：
  - 请求体格式为 JSON（application/json），而非 form-encoded。
  - 请求体具有嵌套结构：外层 params 为数组，内层包含 keywords 列表。
  - 所有关键词统一使用 broad（广泛匹配）。
  - _token 填空字符串（接口不校验此字段）。
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from api_v2.models.ad_upload_queue import AdUploadQueue
from api_v2.models.api_request_log import ParamType
from api_v2.services.ad_creation.ad_lx_client import (
    LX_ADS_API_URL,
    build_lx_headers,
    parse_lx_result,
    write_request_log,
)

logger = logging.getLogger(__name__)


def build_keyword_json_payload(
    profile_id: int,
    campaign_id: str,
    ad_group_id: str,
    keywords: list[str],
) -> dict[str, Any]:
    """构造关键词创建接口的 JSON 请求体。

    外层 params 为含单个元素的数组；内层 params.keywords 包含全部关键词条目，
    每个关键词固定使用 broad（广泛匹配），adGroupId 必须为整型。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 广告活动 ID。
        ad_group_id (str): 广告组 ID。
        keywords (list[str]): 关键词文本列表，不可为空。

    Returns:
        dict[str, Any]: requests.post 的 json 参数字典。
    """
    ad_group_id_int = int(ad_group_id)


    def is_single_word(text: str) -> bool:
        """判断是否为单个单词（仅字母/数字/下划线/不含空格和标点）。"""
        import re
        return bool(re.fullmatch(r"[\w-]+", text))

    keyword_list: list[dict[str, Any]] = []
    for kw in keywords:
        # 支持 kw 为 str 或 dict
        if isinstance(kw, dict):
            text = kw.get("keyword", "")
            monthly_search_volume = kw.get("monthly_search_volume", 0)
        else:
            text = str(kw)
            monthly_search_volume = 0

        # 匹配规则：单个单词或月搜索量>10000为exact，否则broad
        if is_single_word(text) or (isinstance(monthly_search_volume, (int, float)) and monthly_search_volume > 10000):
            match_type = "exact"
        else:
            match_type = "broad"

        keyword_list.append({
            "campaignId": campaign_id,
            "adGroupId": ad_group_id_int,
            "state": "enabled",
            "matchType": match_type,
            "keywordText": text,
        })

    inner_param: dict[str, Any] = {
        "_token": "",
        "api_method": "post_keywords",
        "api_version": "v3",
        "ad_type": "sp",
        "params": {"keywords": keyword_list},
        "profile_id": str(profile_id),
    }

    return {
        "profile_id": str(profile_id),
        "_token": "",
        "api_method": "post_keywords",
        "api_version": "v3",
        "ad_type": "sp",
        "params": [inner_param],
        "one_more": 1,
    }


def build_keyword_headers(
    profile_id: int,
    campaign_id: str,
) -> dict[str, str]:
    """为关键词创建请求构造请求头，覆盖 Content-Type 为 JSON。

    关键词接口使用 JSON 格式提交，需将 Content-Type 覆盖为 application/json；
    referer 中 ad_group_id 固定为 0，与浏览器抓包行为一致。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 广告活动 ID，对应 referer 中的 id 参数。

    Returns:
        dict[str, str]: 修改后的请求头字典。
    """
    referer = (
        f"https://ads.lingxing.com/ad_report/keyword/generate/index"
        f"?profile_id={profile_id}&id={campaign_id}&ad_group_id=0"
    )
    headers = build_lx_headers(
        profile_id=profile_id,
        page_name="/ad_report/keyword/generate/index",
        referer_path=referer,
    )
    # 覆盖 content-type：其他步骤使用 form-encoded，关键词接口使用 JSON
    headers["content-type"] = "application/json;charset=UTF-8"
    return headers


def create_keywords(
    queue: AdUploadQueue,
    profile_id: int,
    campaign_id: str,
    ad_group_id: str,
) -> tuple[list[str], str, str | None]:
    """向领星接口批量提交 MANUAL 广告关键词创建请求。

    queue.keywords 中每个关键词对应 result 列表中的一个条目；
    部分失败视为「异常」，全部失败视为「失败」。
    关键词列表为空时直接返回失败，不发起请求。

    Args:
        queue (AdUploadQueue): 当前队列记录，持有 keywords 字段（关键词文本列表）。
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 第一步创建广告活动后返回的 campaignId。
        ad_group_id (str): 第二步创建广告组后返回的 adGroupId。

    Returns:
        tuple[list[str], str, str | None]:
            - keyword_ids: 成功/异常时所有成功条目的 keywordId 列表；失败时为空列表。
            - status: "SUCCESS" | "ANOMALY" | "FAILED"。
            - details: ANOMALY/FAILED 时的描述；SUCCESS 时为 None。
    """
    raw_keywords: list = (queue.params or {}).get("keywords") or []
    # 居容旧格式（list[str]）与新格式（list[{keyword, monthly_search_volume}]）两种写入
    keywords: list[str] = [
        entry["keyword"] if isinstance(entry, dict) else str(entry)
        for entry in raw_keywords
        if (isinstance(entry, dict) and entry.get("keyword")) or (
            not isinstance(entry, dict) and entry
        )
    ]
    if not keywords:
        logger.warning(
            "[AdKeywordService] 关键词列表为空，跳过关键词提交步骤: id=%s", queue.pk
        )
        return [], "FAILED", "关键词列表为空，MANUAL 广告无法提交关键词"

    payload = build_keyword_json_payload(
        profile_id=profile_id,
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        keywords=keywords,
    )
    headers = build_keyword_headers(profile_id, campaign_id)

    logger.info(
        "[AdKeywordService] 创建关键词: id=%s campaignId=%s adGroupId=%s kw_count=%s",
        queue.pk,
        campaign_id,
        ad_group_id,
        len(keywords),
    )

    try:
        resp = requests.post(
            LX_ADS_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        resp_json: dict[str, Any] = resp.json()
    except requests.RequestException as exc:
        logger.error(
            "[AdKeywordService] HTTP 请求失败: id=%s campaignId=%s err=%s",
            queue.pk,
            campaign_id,
            exc,
            exc_info=True,
        )
        return [], "FAILED", str(exc)

    status, details = parse_lx_result(resp_json)
    if status == "FAILED":
        logger.warning(
            "[AdKeywordService] 关键词创建失败: id=%s campaignId=%s error=%s",
            queue.pk,
            campaign_id,
            details,
        )
        return [], "FAILED", details

    # 收集所有成功条目的 keywordId
    keyword_ids: list[str] = [
        str(item["keywordId"])
        for item in (resp_json.get("result") or [])
        if item.get("code") == "SUCCESS" and item.get("keywordId")
    ]

    logger.info(
        "[AdKeywordService] 关键词创建%s: id=%s campaignId=%s success_count=%s",
        "成功" if status == "SUCCESS" else "异常",
        queue.pk,
        campaign_id,
        len(keyword_ids),
    )
    write_request_log(
        url=LX_ADS_API_URL,
        headers=headers,
        params=payload,
        response_body=resp_json,
        purpose=f"创建关键词: campaignId={campaign_id} adGroupId={ad_group_id} kw_count={len(keywords)}",
        param_type=ParamType.JSON,
    )
    return keyword_ids, status, details
