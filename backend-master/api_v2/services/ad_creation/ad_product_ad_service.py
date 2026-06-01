"""广告投放创建服务（ad_product_ad_service）。

职责：封装向领星 post_productAds 接口批量提交 SKU 广告投放的完整逻辑，
支持一次提交多个 SKU，每个 SKU 对应一条 productAd 条目。
"""

from __future__ import annotations

import logging
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


def build_product_ad_form_data(
    profile_id: int,
    campaign_id: str,
    ad_group_id: str,
    skus: list[str],
) -> dict[str, Any]:
    """构造广告投放创建接口的 form-encoded 请求体。

    每个 SKU 生成一组 params[productAds][N][*] 参数，索引从 0 递增。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 广告活动 ID。
        ad_group_id (str): 广告组 ID。
        skus (list[str]): 待投放的 SKU 列表，不可为空。

    Returns:
        dict[str, Any]: requests.post 的 data 参数字典。
    """
    data: dict[str, Any] = {
        "profile_id": profile_id,
        "api_method": "post_productAds",
        "ad_type": "sp",
        "api_version": "v3",
    }

    for i, sku in enumerate(skus):
        data[f"params[productAds][{i}][campaignId]"] = campaign_id
        data[f"params[productAds][{i}][adGroupId]"] = ad_group_id
        data[f"params[productAds][{i}][state]"] = "enabled"
        data[f"params[productAds][{i}][sku]"] = sku

    return data


def build_product_ad_headers(
    profile_id: int,
    campaign_id: str,
) -> dict[str, str]:
    """为广告投放创建请求构造请求头，覆盖页面名和 referer。

    referer 中 adGroupId 固定为 0，与浏览器实际抓包行为一致。

    Args:
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 广告活动 ID。

    Returns:
        dict[str, str]: 修改后的请求头字典。
    """
    referer = (
        f"https://ads.lingxing.com/ad_report/ad_group/generate/ads"
        f"?profile_id={profile_id}&ref=adg&campaignId={campaign_id}&adGroupId=0"
    )
    return build_lx_headers(
        profile_id=profile_id,
        page_name="/ad_report/ad_group/generate/ads",
        referer_path=referer,
    )


def create_product_ads(
    queue: AdUploadQueue,
    profile_id: int,
    campaign_id: str,
    ad_group_id: str,
    skus_override: list[str] | None = None,
) -> tuple[list[str], str, str | None, list[str]]:
    """向领星接口批量提交广告投放（productAds）创建请求。

    queue.skus 中每个 SKU 对应 result 列表中的一个条目；
    部分失败视为「异常」，全部失败视为「失败」。
    支持传入 skus_override 以便重试时仅提交上次失败的 SKU 子集。

    Args:
        queue (AdUploadQueue): 当前队列记录，持有 skus 字段。
        profile_id (int): 广告 Profile ID。
        campaign_id (str): 第一步创建广告活动后返回的 campaignId。
        ad_group_id (str): 第二步创建广告组后返回的 adGroupId。
        skus_override (list[str] | None): 若不为 None，则以此列表替代
            queue.params["skus"] 作为本次提交的 SKU 集合（用于部分重试）。

    Returns:
        tuple[list[str], str, str | None, list[str]]:
            - product_ad_ids: 成功/异常时所有成功条目的 productAdId 列表；失败时为空列表。
            - status: "SUCCESS" | "ANOMALY" | "FAILED"。
            - details: ANOMALY/FAILED 时的描述；SUCCESS 时为 None。
            - succeeded_skus: 本次提交中成功创建的 SKU 列表（与响应 result 顺序对齐）。
    """
    skus: list[str] = (
        skus_override if skus_override is not None
        else ((queue.params or {}).get("skus") or [])
    )
    if not skus:
        logger.warning(
            "[AdProductAdService] SKU 列表为空，跳过广告投放步骤: id=%s", queue.pk
        )
        return [], "FAILED", "SKU 列表为空，无法创建广告投放", []

    form_data = build_product_ad_form_data(
        profile_id=profile_id,
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        skus=skus,
    )
    headers = build_product_ad_headers(profile_id, campaign_id)

    logger.info(
        "[AdProductAdService] 创建广告投放: id=%s campaignId=%s adGroupId=%s sku_count=%s",
        queue.pk,
        campaign_id,
        ad_group_id,
        len(skus),
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
            "[AdProductAdService] HTTP 请求失败: id=%s campaignId=%s err=%s",
            queue.pk,
            campaign_id,
            exc,
            exc_info=True,
        )
        return [], "FAILED", str(exc), []

    status, details = parse_lx_result(resp_json)

    # "广告商品已存在" 属于幂等场景：SKU 已在亚马逊侧创建，目标状态已达成。
    # 将所有提交的 SKU 视为成功，写入 succeeded_skus 供调度层写入跳过信号，不记录任何异常。
    if status == "FAILED" and details and "已存在" in details:
        logger.info(
            "[AdProductAdService] 广告投放已存在，视为成功（幂等）: id=%s campaignId=%s skus=%s",
            queue.pk,
            campaign_id,
            skus,
        )
        return [], "SUCCESS", None, list(skus)

    if status == "FAILED":
        logger.warning(
            "[AdProductAdService] 广告投放创建失败: id=%s campaignId=%s error=%s",
            queue.pk,
            campaign_id,
            details,
        )
        return [], "FAILED", details, []

    # 通过索引对齐收集成功条目的 productAdId 与对应 SKU
    # Amazon Ads API 批量接口的 result 顺序与提交顺序严格对应
    result_items: list[dict] = resp_json.get("result") or []
    product_ad_ids: list[str] = []
    succeeded_skus: list[str] = []
    for i, item in enumerate(result_items):
        if item.get("code") == "SUCCESS" and item.get("productAdId"):
            product_ad_ids.append(str(item["productAdId"]))
            if i < len(skus):
                succeeded_skus.append(skus[i])

    logger.info(
        "[AdProductAdService] 广告投放创建%s: id=%s campaignId=%s success_count=%s",
        "成功" if status == "SUCCESS" else "异常",
        queue.pk,
        campaign_id,
        len(product_ad_ids),
    )
    write_request_log(
        url=LX_ADS_API_URL,
        headers=headers,
        params=form_data,
        response_body=resp_json,
        purpose=f"创建广告投放: campaignId={campaign_id} adGroupId={ad_group_id} sku_count={len(skus)}",
    )
    return product_ad_ids, status, details, succeeded_skus
