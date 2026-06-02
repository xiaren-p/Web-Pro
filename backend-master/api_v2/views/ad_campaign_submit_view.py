"""广告活动提交视图（ad_campaign_submit_view）。

端点：
  POST /api/v2/ads/submit/  - 触发一次广告活动批量提交，单线程保护。

职责：HTTP 参数解析与响应包装；通过 Django Cache 互斥锁保证同一时刻仅一个请求在执行；
     业务逻辑全部委托 process_pending_campaigns。
"""

import logging

from django.core.cache import cache
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth.bearer_token_auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.services.ad_creation.ad_campaign_submit_service import process_pending_campaigns

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]

# 互斥锁 Cache Key 及最长持有时间（秒）
# 超过此时间后锁自动释放，防止异常导致锁永久占用
_LOCK_KEY = "ad_campaign_submit_running"
_LOCK_TTL = 1500


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def submit_pending_campaigns(request: Request) -> Response:
    """手动触发广告活动批量提交。

    查询 parse_status=SUCCESS && campaign_status=PENDING 的队列记录，
    依次向领星广告接口提交创建请求并回写状态。

    单线程保护：同一时刻仅允许一个请求执行；若已有执行中的请求，
    立即返回 409 Conflict，无需等待。

    Args:
        request (Request): POST 请求，无需 body 参数。

    Returns:
        Response 200: {"total": N, "submitted": N, "failed": N}
        Response 409: {"detail": "任务正在进行中，请稍后再试"}
        Response 500: {"detail": "执行异常: ..."}
    """
    # cache.add 原子操作：Key 不存在时写入并返回 True，已存在时返回 False
    acquired = cache.add(_LOCK_KEY, True, timeout=_LOCK_TTL)
    if not acquired:
        logger.warning(
            "[AdCampaignSubmitView][submit_pending_campaigns] 任务已在执行中，拒绝重入: user=%s",
            request.user,
        )
        return Response(
            {"detail": "任务正在进行中，请稍后再试"},
            status=status.HTTP_409_CONFLICT,
        )

    logger.info(
        "[AdCampaignSubmitView][submit_pending_campaigns] 触发广告批量提交: user=%s",
        request.user,
    )

    try:
        result = process_pending_campaigns()
    except Exception as exc:
        logger.error(
            "[AdCampaignSubmitView][submit_pending_campaigns] 执行异常: %s",
            exc,
            exc_info=True,
        )
        return Response(
            {"detail": f"执行异常: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        # 无论成功/异常，始终释放锁
        cache.delete(_LOCK_KEY)

    logger.info(
        "[AdCampaignSubmitView][submit_pending_campaigns] 完成: total=%s submitted=%s failed=%s",
        result["total"],
        result["submitted"],
        result["failed"],
    )
    return Response(result, status=status.HTTP_200_OK)
