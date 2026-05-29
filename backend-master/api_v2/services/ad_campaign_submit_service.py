"""广告活动 API 提交服务（ad_campaign_submit_service）。

职责：
  1. 查询 parse_status=SUCCESS 且 campaign_status=PENDING 的队列记录。
  2. 通过 LxAdsProfile 按「店铺-国家」匹配 profile_id。
  3. 从青龙缓存读取 LX_ERP_HEADERS，拼接附加请求头。
  4. 向领星广告接口 POST 创建广告活动。
  5. 根据 API 响应更新队列记录的 campaign_status / campaign_response。
  6. 无论成功与否，每次 HTTP 请求均写入 ApiRequestLog 日志表。
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import requests

from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile
from api_v2.models.ad_upload_queue import AdParseStatus, AdUploadQueue
from api_v2.models.api_request_log import ApiRequestLog, HttpMethod, ParamType
from api_v2.services.qinglong_env_service import get_cached_env

logger = logging.getLogger(__name__)

# 领星广告活动创建接口
_API_URL = "https://ads.lingxing.com/ad_report/core/api/handle"

# 固定追加的 HTTP 请求头（在 LX_ERP_HEADERS 基础上叠加，严格对齐真实请求头列表）
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
    "x-ak-ad-page-name": "/ad_report/campaign/generate/index",
    "x-ak-cooperative-key": "0",
    "x-requested-with": "XMLHttpRequest",
}


def _build_headers(profile_id: int) -> dict[str, str]:
    """合并 LX_ERP_HEADERS 缓存值与附加固定请求头。

    Args:
        profile_id (int): 当前操作的广告 profile ID，用于构造 referer。

    Returns:
        dict[str, str]: 最终请求头字典；LX_ERP_HEADERS 未命中时返回仅含附加头的字典。
    """
    raw = get_cached_env("LX_ERP_HEADERS")
    base: dict[str, str] = {}
    if raw:
        try:
            base = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "[AdCampaignSubmitService] LX_ERP_HEADERS JSON 解析失败: %s", exc
            )
    headers = {**base, **_EXTRA_HEADERS}
    headers["referer"] = (
        f"https://ads.lingxing.com/ad_report/campaign/generate/index?profile_id={profile_id}"
    )
    return headers


def _extract_targeting_type(campaign_name: str) -> str:
    """从广告活动名称末尾 token 提取 Amazon targetingType。

    末尾 token 为 "AUTO" → 自动投放；"MANU" → 手动投放（MANUAL）。

    Args:
        campaign_name (str): 带后缀的广告活动名称，如 "X-HLS-LQ-SR AUTO"。

    Returns:
        str: "AUTO" 或 "MANUAL"。
    """
    last_token = campaign_name.strip().rsplit(" ", 1)[-1].upper()
    return "MANUAL" if last_token == "MANU" else "AUTO"


def _find_profile_id(shop: str, country: str) -> int | None:
    """通过「店铺-国家」组合在 LxAdsProfile 中查找 profile_id。

    匹配策略：先精确匹配 name__icontains="{shop}-{country}"，
    未命中时回退为 name__icontains=shop + country_code=country。

    Args:
        shop (str): 队列中的店铺名称。
        country (str): 队列中的国家/站点代码，如 "DE"、"UK"。

    Returns:
        int | None: 匹配到的 profile_id；未匹配返回 None。
    """
    key = f"{shop}-{country}"
    profile = LxAdsProfile.objects.filter(name__icontains=key).first()
    if profile is None:
        profile = (
            LxAdsProfile.objects
            .filter(name__icontains=shop, country_code__iexact=country)
            .first()
        )
    if profile is None:
        logger.warning(
            "[AdCampaignSubmitService] 未找到匹配的 profile: shop=%s country=%s",
            shop,
            country,
        )
        return None
    return int(profile.profile_id)


def _build_form_data(
    profile_id: int,
    campaign_name: str,
    targeting_type: str,
    ad_type: str,
) -> dict[str, Any]:
    """构造广告活动创建接口的 form-encoded 请求体。

    按照真实请求参数模板构造，仅 profile_id / name / targetingType / startDate 动态填充；
    其余固定参数与模板保持一致，不做任何调整。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_name (str): 广告活动名称（含 AUTO/MANU 后缀）。
        targeting_type (str): Amazon 广告定向类型，"AUTO" 或 "MANUAL"。
        ad_type (str): 广告类型，如 "sp"。

    Returns:
        dict[str, Any]: requests.post 的 data 参数字典。
    """
    today = date.today().isoformat()
    data: dict[str, Any] = {
        "profile_id": profile_id,
        "api_method": "post_campaigns",
        "params[campaigns][0][state]": "ENABLED",
        "params[campaigns][0][name]": campaign_name,
        "params[campaigns][0][targetingType]": targeting_type,
        "params[campaigns][0][startDate]": today,
        "params[campaigns][0][endDate]": "",
        "params[campaigns][0][budget][budgetType]": "DAILY",
        "params[campaigns][0][budget][budget]": 1,
        "params[campaigns][0][dynamicBidding][strategy]": "MANUAL",
        "params[campaigns][0][dynamicBidding][placementBidding][0][placement]": "PLACEMENT_TOP",
        "params[campaigns][0][dynamicBidding][placementBidding][0][percentage]": 0,
        "params[campaigns][0][dynamicBidding][placementBidding][1][placement]": "PLACEMENT_REST_OF_SEARCH",
        "params[campaigns][0][dynamicBidding][placementBidding][1][percentage]": 0,
        "params[campaigns][0][dynamicBidding][placementBidding][2][placement]": "PLACEMENT_PRODUCT_PAGE",
        "params[campaigns][0][dynamicBidding][placementBidding][2][percentage]": 0,
        "params[campaigns][0][dynamicBidding][placementBidding][3][placement]": "SITE_AMAZON_BUSINESS",
        "params[campaigns][0][dynamicBidding][placementBidding][3][percentage]": 0,
        "ad_type": ad_type,
        "api_version": "v3",
    }
    return data


def _write_request_log(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    response_body: dict[str, Any],
    purpose: str,
) -> None:
    """将对外 HTTP 请求记录写入 ApiRequestLog 日志表。

    所有对外请求均应调用本函数，无论成功与否。异常不向上传播以避免影响主流程。

    Args:
        url (str): 请求 URL。
        headers (dict[str, str]): 实际发送的请求头。
        params (dict[str, Any]): 请求传参（form-encoded 字典）。
        response_body (dict[str, Any]): 接口响应内容（HTTP 异常时为错误字典）。
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
        logger.error(
            "[AdCampaignSubmitService] 写入请求日志失败: %s",
            exc,
            exc_info=True,
        )


def _parse_result_error(resp_json: dict[str, Any]) -> str | None:
    """从领星接口响应中提取业务级错误描述。

    领星广告接口无论成功与否均返回 HTTP 200，result 条目始终包含 "code" 字段。
    区分成功与失败的依据是 code 值是否以 "Error" 结尾（大小写不敏感）：
    - code 以 "Error" 结尾（如 "dateError"） → 创建失败，提取 descriptionCn，回退到 description。
    - code 不以 "Error" 结尾                 → 创建成功，返回 None。
    - result 为空                             → 创建成功，返回 None。

    Args:
        resp_json (dict[str, Any]): 接口原始响应字典。

    Returns:
        str | None: 失败时返回错误描述字符串；成功时返回 None。
    """
    result: list[dict[str, Any]] = resp_json.get("result") or []
    for item in result:
        code = str(item.get("code", ""))
        if code.lower().endswith("error"):
            return item.get("descriptionCn") or item.get("description") or "未知错误"
    return None


def _submit_single(queue: AdUploadQueue) -> None:
    """处理单条队列记录，向领星接口提交广告活动并更新提交状态。

    领星接口始终返回 HTTP 200，真实成功/失败通过响应体 result 数组判断：
    - result 为空列表 → 创建成功，campaign_status=SUCCESS。
    - result 非空     → 创建失败，campaign_status=FAILED，msg 写入 descriptionCn（description 兜底）。

    Args:
        queue (AdUploadQueue): 待提交的队列记录实例。
    """
    profile_id = _find_profile_id(queue.shop, queue.country)
    if profile_id is None:
        queue.parse_status = AdParseStatus.FAILED
        queue.msg = f"未找到匹配 profile: {queue.shop}-{queue.country}"
        queue.save(update_fields=["parse_status", "msg"])
        return

    targeting_type = _extract_targeting_type(queue.campaign_name)
    form_data = _build_form_data(profile_id, queue.campaign_name, targeting_type, queue.ad_type)
    headers = _build_headers(profile_id)

    logger.info(
        "[AdCampaignSubmitService] 提交广告活动: id=%s campaign=%s profile=%s",
        queue.pk,
        queue.campaign_name,
        profile_id,
    )

    try:
        resp = requests.post(
            _API_URL,
            data=form_data,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        resp_json: dict[str, Any] = resp.json()
    except requests.RequestException as exc:
        logger.error(
            "[AdCampaignSubmitService] HTTP 请求失败: id=%s campaign=%s err=%s",
            queue.pk,
            queue.campaign_name,
            exc,
            exc_info=True,
        )
        queue.parse_status = AdParseStatus.FAILED
        queue.msg = str(exc)
        queue.save(update_fields=["parse_status", "msg"])
        return

    # 领星接口始终返回 HTTP 200，真实失败通过 result 数组非空体现
    error_msg = _parse_result_error(resp_json)
    if error_msg is None:
        logger.info(
            "[AdCampaignSubmitService] 提交成功: id=%s campaign=%s",
            queue.pk,
            queue.campaign_name,
        )
        queue.parse_status = AdParseStatus.SUCCESS
        queue.msg = "成功"
        queue.save(update_fields=["parse_status", "msg"])
        _write_request_log(
            url=_API_URL,
            headers=headers,
            params=form_data,
            response_body=resp_json,
            purpose=f"创建广告活动: {queue.campaign_name}",
        )
    else:
        logger.warning(
            "[AdCampaignSubmitService] 接口业务失败: id=%s campaign=%s error=%s",
            queue.pk,
            queue.campaign_name,
            error_msg,
        )
        queue.parse_status = AdParseStatus.FAILED
        queue.msg = error_msg
        queue.save(update_fields=["parse_status", "msg"])


def process_pending_campaigns() -> dict[str, int]:
    """批量处理所有待提交（parse_status=SUCCESS, campaign_status=PENDING）的队列记录。

    逐条调用 _submit_single，独立处理每条记录，单条异常不影响其余记录。

    Returns:
        dict[str, int]: 含 total / submitted / failed 三个计数字段的结果摘要。
    """
    pending_qs = AdUploadQueue.objects.filter(
        parse_status=AdParseStatus.PENDING,
    ).order_by("id")

    total = pending_qs.count()
    if total == 0:
        logger.debug("[AdCampaignSubmitService] 无待提交队列记录，跳过。")
        return {"total": 0, "submitted": 0, "failed": 0}

    logger.info("[AdCampaignSubmitService] 开始批量提交，共 %s 条。", total)

    submitted = 0
    failed = 0
    for queue in pending_qs.iterator():
        try:
            _submit_single(queue)
            if queue.parse_status == AdParseStatus.SUCCESS:
                submitted += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            logger.error(
                "[AdCampaignSubmitService] 处理队列记录异常: id=%s err=%s",
                queue.pk,
                exc,
                exc_info=True,
            )

    logger.info(
        "[AdCampaignSubmitService] 批量提交完成: total=%s submitted=%s failed=%s",
        total,
        submitted,
        failed,
    )
    return {"total": total, "submitted": submitted, "failed": failed}
