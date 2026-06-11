"""SP 广告优化策略——手动触发接口。

仅负责入队 Celery 任务并立即返回，避免在 gunicorn worker 进程中同步执行重匹配操作。
"""
import logging

from django.core.cache import cache
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.tasks.optimization_strategy_task import run_optimization_strategy_task

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]

_OPT_STRATEGY_LOCK_KEY = "sp_ad_optimization_strategy_lock"
_OPT_STRATEGY_LOCK_TTL = 1800


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_optimization_strategy(request: Request) -> Response:
    """SP 广告优化策略匹配：扫描开启的广告活动，匹配 LxAdRule 优化规则，写入策略记录。

    委托 Celery 异步执行。
    使用 Redis 分布式锁保证同一时刻只有一个触发实例。
    锁在入队成功后立即释放——TTL（30 分钟）仅作异常兜底。

    Args:
        request: DRF Request 对象

    Returns:
        Response: 成功时返回 {"code": "00000", "data": {"task_id": ...}, "msg": "..."}
                  并发冲突时返回 {"code": "B0001", ...} status=409
    """
    if not cache.add(_OPT_STRATEGY_LOCK_KEY, "1", timeout=_OPT_STRATEGY_LOCK_TTL):
        return Response(
            {"code": "B0001", "data": None, "msg": "优化策略任务正在执行中"},
            status=409,
        )

    try:
        result = run_optimization_strategy_task.delay()
    except Exception:
        logger.exception("[trigger_optimization_strategy] Celery 入队失败")
        return Response(
            {"code": "B0002", "data": None, "msg": "Celery 任务入队失败，请稍后重试"},
            status=500,
        )
    finally:
        cache.delete(_OPT_STRATEGY_LOCK_KEY)

    return Response({
        "code": "00000",
        "data": {"task_id": str(result.id)},
        "msg": "优化策略任务已入队，将由 Celery 异步执行",
    })
