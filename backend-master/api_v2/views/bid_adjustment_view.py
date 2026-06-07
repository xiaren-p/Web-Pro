"""竞价调整——手动触发接口。

注意：此接口仅负责入队 Celery 任务并立即返回，避免在 gunicorn worker
      进程中同步执行 API 调用导致超时被 kill。
"""
import logging

from django.core.cache import cache
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.tasks.bid_adjustment_task import run_bid_adjustment_task

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]

_BID_ADJUST_LOCK_KEY = "bid_adjustment_lock"


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_bid_adjustment(request: Request) -> Response:
    """手动触发竞价调整任务，委托 Celery 异步执行。

    并发控制：
      使用 Redis 分布式锁保证同一时刻只有一个触发实例。
      锁在入队成功后立即释放 —— TTL（30 分钟）仅作异常兜底。

    Args:
        request: DRF Request 对象

    Returns:
        Response: 成功时返回 {"code": "00000", "data": {task_id}, "msg": "..."}
                  并发冲突时返回 {"code": "B0001", ...} status=409
    """
    if not cache.add(_BID_ADJUST_LOCK_KEY, "1", timeout=1800):
        return Response(
            {"code": "B0001", "data": None, "msg": "竞价调整任务正在执行中"},
            status=409,
        )

    try:
        task = run_bid_adjustment_task.delay()
    except Exception:
        logger.exception("[trigger_bid_adjustment] Celery 入队失败")
        return Response(
            {"code": "B0002", "data": None, "msg": "Celery 任务入队失败，请稍后重试"},
            status=500,
        )
    finally:
        # 入队成功后立即释放锁（正常路径），TTL 仅作异常兜底
        cache.delete(_BID_ADJUST_LOCK_KEY)

    return Response({
        "code": "00000",
        "data": {"task_id": str(task.id), "message": "竞价调整任务已入队"},
        "msg": "success",
    })