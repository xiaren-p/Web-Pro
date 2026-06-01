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
import re
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


def sanitize_keyword_text(text: str) -> str:
    """清洗关键词文本，移除标点符号并压缩多余空白。

    Args:
        text (str): 原始关键词文本。

    Returns:
        str: 去除标点后的关键词文本。
    """
    # 仅保留 Unicode 字母/数字/下划线与空白；其余符号（含中西文标点）统一移除。
    sanitized = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", sanitized, flags=re.UNICODE).strip()


def build_keyword_json_payload(
    profile_id: int,
    campaign_id: str,
    ad_group_id: str,
    keywords: list,
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

        sanitized_text = sanitize_keyword_text(text)

        # 匹配规则：单个单词或月搜索量>10000为exact，否则broad
        if is_single_word(sanitized_text) or (
            isinstance(monthly_search_volume, (int, float)) and monthly_search_volume > 10000
        ):
            match_type = "exact"
        else:
            match_type = "broad"

        keyword_list.append({
            "campaignId": campaign_id,
            "adGroupId": ad_group_id_int,
            "state": "enabled",
            "matchType": match_type,
            "keywordText": sanitized_text,
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
    keywords_override: list | None = None,
) -> tuple[list[str], str, str | None, list[str]]:
    """向领星接口批量提交 MANUAL 广告关键词创建请求。

    queue.keywords 中每个关键词对应 result 列表中的一个条目；
    部分失败视为「异常」，全部失败视为「失败」。
    关键词列表为空时直接返回失败，不发起请求。
    支持传入 keywords_override 以便重试时仅提交上次失败的关键词子集。

    Args:
        queue (AdUploadQueue): 当前队列记录，持有 keywords 字段（关键词文本列表）。
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 第一步创建广告活动后返回的 campaignId。
        ad_group_id (str): 第二步创建广告组后返回的 adGroupId。
        keywords_override (list | None): 若不为 None，则以此列表替代
            queue.params["keywords"] 作为本次提交的关键词集合（用于部分重试）。

    Returns:
        tuple[list[str], str, str | None, list[str]]:
            - keyword_ids: 成功/异常时所有成功条目的 keywordId 列表；失败时为空列表。
            - status: "SUCCESS" | "ANOMALY" | "FAILED"。
            - details: ANOMALY/FAILED 时的描述；SUCCESS 时为 None。
            - succeeded_keyword_texts: 本次提交中成功创建的关键词文本列表（与响应顺序对齐）。
    """
    raw_keywords: list = (
        keywords_override if keywords_override is not None
        else ((queue.params or {}).get("keywords") or [])
    )

    # 预校验：过滤超过 Amazon 10 词限制的关键词，防止整批被拒（Amazon 对单个关键词超限会拒绝整个请求）
    valid_raw: list = []
    skipped_kws: list[str] = []
    for entry in raw_keywords:
        text = entry["keyword"] if isinstance(entry, dict) else str(entry)
        if not text:
            continue
        if len(text.split()) > 10:
            skipped_kws.append(text)
        else:
            valid_raw.append(entry)

    if skipped_kws:
        logger.warning(
            "[AdKeywordService] 关键词超过10词限制，已跳过提交: id=%s skipped=%s",
            queue.pk, skipped_kws,
        )

    # 兼容旧格式（list[str]）与新格式（list[{keyword, monthly_search_volume}]）
    keywords: list[str] = [
        entry["keyword"] if isinstance(entry, dict) else str(entry)
        for entry in valid_raw
    ]

    if not keywords:
        detail = "关键词列表为空，MANUAL 广告无法提交关键词"
        if skipped_kws:
            detail = f"所有关键词均超过10个单词的 Amazon 限制，无法提交："
            detail += "；".join(skipped_kws)
        logger.warning("[AdKeywordService] %s id=%s", detail, queue.pk)
        return [], "FAILED", detail, []

    # 预校验跳过的说明，将在最终状态中与 API 响应合并
    skip_detail: str | None = (
        f"以下关键词超过10词已跳过："
        + "；".join(skipped_kws)
    ) if skipped_kws else None

    # 传入 valid_raw（str 或 dict），使 build_keyword_json_payload 能正确读取 monthly_search_volume
    payload = build_keyword_json_payload(
        profile_id=profile_id,
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        keywords=valid_raw,
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
        return [], "FAILED", str(exc), []

    # ── 幂等处理："关键词已存在"视为已完成，不阻塞流程 ─────────────────────────────
    # 领星 API 对重复关键词返回"关键词已存在"，业务语义上等同于幂等成功。
    # 需从 entityAndReason 和 result[] 两处同时识别，避免 parse_lx_result 误判为失败。
    raw_entity_reasons: list[dict] = resp_json.get("entityAndReason") or []
    raw_result_items: list[dict] = resp_json.get("result") or []

    # 1. 从 entityAndReason 收集"已存在"的关键词文本
    already_exists_texts: set[str] = {
        er["entityName"]
        for er in raw_entity_reasons
        if er.get("entityName")
        and "已存在" in (er.get("descriptionCn") or er.get("description") or "")
    }

    # 2. 从 result[] 按索引对齐补充（部分接口仅在 result 条目中描述错误）
    for i, item in enumerate(raw_result_items):
        desc = item.get("description") or item.get("descriptionCn") or ""
        if "已存在" in desc and i < len(keywords):
            already_exists_texts.add(keywords[i])

    # 3. 构造过滤"已存在"后的虚拟响应，用于 parse_lx_result 状态判断
    if already_exists_texts:
        filtered_entity_reasons = [
            er for er in raw_entity_reasons
            if not (
                er.get("entityName") in already_exists_texts
                and "已存在" in (er.get("descriptionCn") or er.get("description") or "")
            )
        ]
        # 将"已存在"对应的 result 条目替换为虚拟 SUCCESS 占位（无 keywordId）
        filtered_results = [
            (
                {"code": "SUCCESS"}
                if (
                    i < len(keywords)
                    and keywords[i] in already_exists_texts
                    and item.get("code") != "SUCCESS"
                )
                else item
            )
            for i, item in enumerate(raw_result_items)
        ]
        resp_for_parse: dict = {
            **resp_json,
            "result": filtered_results,
            "entityAndReason": filtered_entity_reasons,
        }
    else:
        resp_for_parse = resp_json

    if already_exists_texts:
        logger.info(
            "[AdKeywordService] 关键词已存在（幂等忽略）: id=%s count=%s keywords=%s",
            queue.pk,
            len(already_exists_texts),
            list(already_exists_texts),
        )

    status, details = parse_lx_result(resp_for_parse)

    # 合并预校验跳过的关键词说明到最终状态
    if skip_detail:
        if status == "SUCCESS":
            status = "ANOMALY"
            details = skip_detail
        else:
            details = f"{details}；{skip_detail}" if details else skip_detail

    if status == "FAILED":
        logger.warning(
            "[AdKeywordService] 关键词创建失败: id=%s campaignId=%s error=%s",
            queue.pk,
            campaign_id,
            details,
        )
        return [], "FAILED", details, []

    # 通过索引对齐收集成功条目的 keywordId 与对应关键词文本
    # Amazon Ads API 批量接口的 result 顺序与提交顺序严格对应
    # "关键词已存在"的条目无 keywordId，但同样计入 succeeded_keyword_texts
    keyword_ids: list[str] = []
    succeeded_keyword_texts: list[str] = []
    for i, item in enumerate(raw_result_items):
        kw_text: str | None = keywords[i] if i < len(keywords) else None
        if item.get("code") == "SUCCESS" and item.get("keywordId"):
            keyword_ids.append(str(item["keywordId"]))
            if kw_text:
                succeeded_keyword_texts.append(kw_text)
        elif kw_text and kw_text in already_exists_texts:
            # 关键词已存在：幂等成功，无 keywordId 但标记为已完成防止重复提交
            succeeded_keyword_texts.append(kw_text)

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
    return keyword_ids, status, details, succeeded_keyword_texts
