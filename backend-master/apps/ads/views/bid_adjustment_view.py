"""竞价调整——手动触发接口。

注意：此接口仅负责入队 Celery 任务并立即返回，避免在 gunicorn worker
      进程中同步执行 API 调用导致超时被 kill。
"""
import logging

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from apps.ads.tasks.bid_adjustment_task import LOCK_KEY, run_bid_adjustment_task
from api_v2.utils.task_execution_lock import BUSY_RESPONSE, is_task_running

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_bid_adjustment(request: Request) -> Response:
    """手动触发竞价调整任务，委托 Celery 异步执行。

    并发控制：
      调度前检查任务执行锁，被占即返回 409。
      锁的占用 / 释放由任务体 ``TaskExecutionLock`` 负责，视图只读不写。

    Args:
        request: DRF Request 对象

    Returns:
        Response: 成功时返回 {"code": "00000", "data": {task_id}, "msg": "..."}
                  并发冲突时返回 {"code": "B0001", ...} status=409
    """
    if is_task_running(LOCK_KEY):
        return Response(BUSY_RESPONSE("竞价调整任务正在执行中"), status=409)

    try:
        task = run_bid_adjustment_task.delay()
    except Exception:
        logger.exception("[trigger_bid_adjustment] Celery 入队失败")
        return Response(
            {"code": "B0002", "data": None, "msg": "Celery 任务入队失败，请稍后重试"},
            status=500,
        )

    return Response({
        "code": "00000",
        "data": {"task_id": str(task.id), "message": "竞价调整任务已入队"},
        "msg": "success",
    })
