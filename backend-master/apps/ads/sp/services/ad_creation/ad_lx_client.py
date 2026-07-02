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


def parse_lx_result(resp_json: dict[str, Any]) -> tuple[str, str | None]:
    """解析领星接口响应，将结果分类为成功 / 异常 / 失败三档。

    分类规则：
    1. 顶层 code != 200 → "FAILED"（服务端错误）。
    2. 全部 result[].code == "SUCCESS" 且 entityAndReason 为空 → "SUCCESS"。
    3. 部分 result[].code == "SUCCESS"，其余失败 → "ANOMALY"（部分成功，不中止后续步骤）。
    4. 无任何 result[].code == "SUCCESS" → "FAILED"。

    错误/异常描述优先从 entityAndReason 拼合（entityName + descriptionCn/description），
    兜底取首个失败 result 条目的 description 或 code。

    Args:
        resp_json (dict[str, Any]): 接口原始响应字典。

    Returns:
        tuple[str, str | None]:
            - status: "SUCCESS" | "ANOMALY" | "FAILED"。
            - details: ANOMALY/FAILED 时的描述文本；SUCCESS 时为 None。
    """
    top_code = resp_json.get("code")
    if top_code != 200:
        msg = resp_json.get("message") or f"接口返回错误码 {top_code}"
        return "FAILED", msg

    result: list[dict[str, Any]] = resp_json.get("result") or []
    entity_reasons: list[dict[str, Any]] = resp_json.get("entityAndReason") or []

    succeeded = [r for r in result if r.get("code") == "SUCCESS"]
    failed = [r for r in result if r.get("code") != "SUCCESS"]

    # 全部成功且无异常条目 → 成功
    if not failed and not entity_reasons:
        return "SUCCESS", None

    # 构造错误/异常描述
    if entity_reasons:
        parts: list[str] = []
        for er in entity_reasons:
            name: str = er.get("entityName") or ""
            desc: str = er.get("descriptionCn") or er.get("description") or ""
            parts.append(f"{name}: {desc}" if name else desc)
        details: str = "；".join(p for p in parts if p) or "部分操作异常"
    elif failed:
        first = failed[0]
        details = first.get("description") or first.get("code") or "未知错误"
    else:
        details = "部分操作失败"

    # 有成功条目 → 异常（部分成功）；无成功条目 → 完全失败
    if succeeded:
        return "ANOMALY", details
    return "FAILED", details


def write_request_log(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    response_body: dict[str, Any],
    purpose: str,
    param_type: str = ParamType.FORM,
) -> None:
    """将对外 HTTP 请求记录写入 ApiRequestLog 日志表。

    异常不向上传播，避免影响主流程。

    Args:
        url (str): 请求 URL。
        headers (dict[str, str]): 实际发送的请求头。
        params (dict[str, Any]): 请求传参（form 字典或 JSON 对象）。
        response_body (dict[str, Any]): 接口响应内容。
        purpose (str): 本次请求的作用描述。
        param_type (str): 传参方式，默认为 ParamType.FORM；传入 ParamType.JSON 适用于 JSON 体请求。
    """
    try:
        ApiRequestLog.objects.create(
            url=url,
            method=HttpMethod.POST,
            param_type=param_type,
            request_headers=headers,
            request_params=params,
            response_body=response_body,
            purpose=purpose,
        )
    except Exception as exc:
        logger.error("[AdLxClient] 写入请求日志失败: %s", exc, exc_info=True)
