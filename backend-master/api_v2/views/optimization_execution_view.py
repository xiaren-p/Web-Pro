"""SP 广告优化策略执行——手动触发接口。

委托 Celery 异步执行策略规则。
"""
import logging

from django.core.cache import cache
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.tasks.optimization_execution_task import run_optimization_execution_task

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]

_EXEC_LOCK_KEY = "sp_ad_optimization_execution_lock"
_EXEC_LOCK_TTL = 1800


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_optimization_execution(request: Request) -> Response:
    """SP 广告优化策略执行：扫描已命中的规则，按维度执行操作。

    委托 Celery 异步执行。
    Redis 锁在入队成功后立即释放。

    Args:
        request: DRF Request 对象

    Returns:
        Response: {"code": "00000", "data": {"task_id": ...}, "msg": "..."}
    """
    if not cache.add(_EXEC_LOCK_KEY, "1", timeout=_EXEC_LOCK_TTL):
        return Response(
            {"code": "B0001", "data": None, "msg": "优化策略执行任务正在执行中"},
            status=409,
        )

    try:
        result = run_optimization_execution_task.delay()
    except Exception:
        logger.exception("[trigger_optimization_execution] Celery 入队失败")
        return Response(
            {"code": "B0002", "data": None, "msg": "Celery 任务入队失败，请稍后重试"},
            status=500,
        )
    finally:
        cache.delete(_EXEC_LOCK_KEY)

    return Response({
        "code": "00000",
        "data": {"task_id": str(result.id)},
        "msg": "优化策略执行任务已入队，将由 Celery 异步执行",
    })
