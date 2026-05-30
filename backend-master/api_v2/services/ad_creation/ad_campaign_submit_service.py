"""广告提交调度服务（ad_campaign_submit_service）。

职责：
  1. 查询 parse_status=PENDING 的队列记录。
  2. 通过 LxAdsProfile 按「店铺-国家」匹配 profile_id。
  3. 调度第一步（创建广告活动）和第二步（创建广告组），按结果写入最终状态。

HTTP 请求细节、请求体构造、响应解析分别由以下模块负责：
  - api_v2.services.ad_lx_client        — 底层共享客户端工具
  - api_v2.services.ad_campaign_service — 广告活动（Step 1）
  - api_v2.services.ad_group_service    — 广告组（Step 2）
"""

from __future__ import annotations

import logging

from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile
from api_v2.models.ad_upload_queue import AdParseStatus, AdUploadQueue
from api_v2.services.ad_creation.ad_campaign_service import create_campaign
from api_v2.services.ad_creation.ad_group_service import create_ad_group

logger = logging.getLogger(__name__)


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


def _submit_single(queue: AdUploadQueue) -> None:
    """处理单条队列记录的完整两阶段提交流程。

    第一步：调用 create_campaign 创建广告活动，成功后获取 campaignId。
    第二步：调用 create_ad_group 创建广告组，AUTO 广告同步提交四种自动定向竞价。
    任一步骤失败均将 parse_status 置为 FAILED 并写入错误描述。

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

    # ── 第一步：创建广告活动 ─────────────────────────────────────────────────────
    campaign_id, campaign_error = create_campaign(queue, profile_id, targeting_type)
    if campaign_error:
        queue.parse_status = AdParseStatus.FAILED
        queue.msg = campaign_error
        queue.save(update_fields=["parse_status", "msg"])
        return

    # ── 第二步：创建广告组 ───────────────────────────────────────────────────────
    ag_error = create_ad_group(queue, profile_id, campaign_id, targeting_type)
    if ag_error:
        queue.parse_status = AdParseStatus.FAILED
        queue.msg = f"广告活动已创建（{campaign_id}），广告组创建失败：{ag_error}"
        queue.save(update_fields=["parse_status", "msg"])
        return

    queue.parse_status = AdParseStatus.SUCCESS
    queue.msg = "成功"
    queue.save(update_fields=["parse_status", "msg"])


def process_pending_campaigns() -> dict[str, int]:
    """批量处理所有待提交（parse_status=PENDING）的队列记录。

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