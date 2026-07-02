"""广告活动提交视图（ad_campaign_submit_view）。

端点：
  POST /api/v2/ads/submit/  - 触发一次广告活动批量提交，单线程保护。

职责：HTTP 参数解析与响应包装；通过共享的任务执行锁保证同一时刻仅一个请求/Celery 在执行；
     业务逻辑全部委托 process_pending_campaigns。
"""

import logging

from django.core.cache import cache
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from apps.system.auth.bearer_token_auth import BearerTokenAuthentication
from apps.system.permissions.api_access import IsApiAccessible
from apps.ads.sp.rules.services.ad_creation.ad_campaign_submit_service import process_pending_campaigns
from apps.ads.sp.rules.tasks.ad_campaign_submit_task import LOCK_KEY, LOCK_TTL
from apps.common.utils.task_execution_lock import is_task_running

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsApiAccessible]


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def submit_pending_campaigns(request: Request) -> Response:
    """手动触发广告活动批量提交。

    查询 parse_status=SUCCESS && campaign_status=PENDING 的队列记录，
    依次向领星广告接口提交创建请求并回写状态。

    并发控制：
      与 Celery 任务 submit_pending_campaigns_task 共用同一把 LOCK_KEY，
      若 Celery 任务正在执行（cache 中存在该 key），视图直接返回 409；
      若没有 Celery 任务，则视图本身用 cache.add 占锁、同步执行业务、释放锁。

    Args:
        request (Request): POST 请求，无需 body 参数。

    Returns:
        Response 200: {"total": N, "submitted": N, "failed": N}
        Response 409: {"detail": "任务正在进行中，请稍后再试"}
        Response 500: {"detail": "执行异常: ..."}
    """
    # 先检查 Celery 任务是否在跑（被任务体的 TaskExecutionLock 占着）
    if is_task_running(LOCK_KEY):
        logger.warning(
            "[AdCampaignSubmitView][submit_pending_campaigns] Celery 任务在跑，拒绝同步触发: user=%s",
            request.user,
        )
        return Response(
            {"detail": "任务正在进行中，请稍后再试"},
            status=status.HTTP_409_CONFLICT,
        )

    # 视图自己也尝试占锁，防止两次 HTTP 同时进入（cache.add 原子操作）
    acquired = cache.add(LOCK_KEY, True, timeout=LOCK_TTL)
    if not acquired:
        logger.warning(
            "[AdCampaignSubmitView][submit_pending_campaigns] 视图层抢锁失败，拒绝重入: user=%s",
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
        cache.delete(LOCK_KEY)

    logger.info(
        "[AdCampaignSubmitView][submit_pending_campaigns] 完成: total=%s submitted=%s failed=%s",
        result["total"],
        result["submitted"],
        result["failed"],
    )
    return Response(result, status=status.HTTP_200_OK)
