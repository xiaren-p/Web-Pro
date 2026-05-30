"""领星广告接口底层共享客户端（ad_lx_client）。

职责：
  - 提供统一的 API URL 常量。
  - 从青龙缓存读取 LX_ADS_HEADERS 并与固定附加头合并。
  - 解析领星接口业务级错误。
  - 写入对外 HTTP 请求日志。

本模块不包含任何业务逻辑，仅供 ad_campaign_service / ad_group_service 等模块复用。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from api_v2.models.api_request_log import ApiRequestLog, HttpMethod, ParamType
from api_v2.services.qinglong_env_service import get_cached_env

logger = logging.getLogger(__name__)

# 领星广告统一接口入口
LX_ADS_API_URL = "https://ads.lingxing.com/ad_report/core/api/handle"

# 固定追加的 HTTP 请求头（在 LX_ADS_HEADERS 基础上叠加）
_EXTRA_HEADERS: dict[str, str] = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "connection": "keep-alive",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://ads.lingxing.com",
    "sec-ch-ua": '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-ak-cooperative-key": "0",
    "x-requested-with": "XMLHttpRequest",
}


def build_lx_headers(
    profile_id: int,
    page_name: str = "/ad_report/campaign/generate/index",
    referer_path: str | None = None,
) -> dict[str, str]:
    """合并 LX_ADS_HEADERS 缓存值与附加固定请求头。

    ads.lingxing.com 接口使用 Cookie 鉴权，必须使用包含 Cookie 字段的 LX_ADS_HEADERS。

    Args:
        profile_id (int): 当前操作的广告 profile ID，用于构造默认 referer。
        page_name (str): 注入至 x-ak-ad-page-name 请求头的页面路径。
        referer_path (str | None): 完整 referer URL；为 None 时自动按 profile_id 构造。

    Returns:
        dict[str, str]: 最终请求头字典；LX_ADS_HEADERS 未命中时仅含附加头。
    """
    raw = get_cached_env("LX_ADS_HEADERS")
    base: dict[str, str] = {}
    if not raw:
        logger.warning(
            "[AdLxClient] LX_ADS_HEADERS 缓存为空，将以无认证头发起请求，预计返回 401。"
            "请检查：① 青龙同步任务是否运行 ② 青龙中 LX_ADS_HEADERS 是否存在且非空。"
        )
    else:
        try:
            base = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("[AdLxClient] LX_ADS_HEADERS JSON 解析失败: %s", exc)

    headers = {**base, **_EXTRA_HEADERS}
    headers["x-ak-ad-page-name"] = page_name
    if referer_path is not None:
        headers["referer"] = referer_path
    else:
        headers["referer"] = (
            f"https://ads.lingxing.com/ad_report/campaign/generate/index"
            f"?profile_id={profile_id}"
        )
    return headers


def parse_lx_result_error(resp_json: dict[str, Any]) -> str | None:
    """从领星接口响应中提取业务级错误描述。

    判断规则：
    1. 顶层 code != 200 → 服务端拒绝，提取 message 作为错误描述。
    2. code == 200 且 result[] 含 code 以 "Error" 结尾的条目 → 业务失败；
       中文描述优先从 entityAndReason[].descriptionCn 提取，回退到 result[].description。
    3. code == 200 且无任何错误条目 → 成功，返回 None。

    Args:
        resp_json (dict[str, Any]): 接口原始响应字典。

    Returns:
        str | None: 失败时返回错误描述；成功返回 None。
    """
    top_code = resp_json.get("code")
    if top_code != 200:
        return resp_json.get("message") or f"接口返回错误码 {top_code}"

    result: list[dict[str, Any]] = resp_json.get("result") or []
    error_items = [
        item for item in result
        if str(item.get("code", "")).lower().endswith("error")
    ]
    if not error_items:
        return None

    entity_reasons: list[dict[str, Any]] = resp_json.get("entityAndReason") or []
    cn_desc = next(
        (e.get("descriptionCn") for e in entity_reasons if e.get("descriptionCn")),
        None,
    )
    if cn_desc:
        return cn_desc
    return error_items[0].get("description") or "未知错误"


def write_request_log(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    response_body: dict[str, Any],
    purpose: str,
) -> None:
    """将对外 HTTP 请求记录写入 ApiRequestLog 日志表。

    异常不向上传播，避免影响主流程。

    Args:
        url (str): 请求 URL。
        headers (dict[str, str]): 实际发送的请求头。
        params (dict[str, Any]): 请求传参（form-encoded 字典）。
        response_body (dict[str, Any]): 接口响应内容。
        purpose (str): 本次请求的作用描述。
    """
    try:
        ApiRequestLog.objects.create(
            url=url,
            method=HttpMethod.POST,
            param_type=ParamType.FORM,
            request_headers=headers,
            request_params=params,
            response_body=response_body,
            purpose=purpose,
        )
    except Exception as exc:
        logger.error("[AdLxClient] 写入请求日志失败: %s", exc, exc_info=True)
