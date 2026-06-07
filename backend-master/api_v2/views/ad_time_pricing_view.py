"""广告分时策略——手动触发接口。

注意：此接口仅负责入队 Celery 任务并立即返回 202，避免在 gunicorn worker
      进程中同步执行重 DB / 重内存操作导致超时被 kill。
"""
from django.core.cache import cache
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.tasks.ad_time_pricing_task import run_ad_time_pricing_task
from api_v2.tasks.time_pricing_task import run_time_pricing_task

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]

_TIME_PRICING_LOCK_KEY = "time_pricing_lock"


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_time_pricing(request: Request) -> Response:
    """分时策略一键执行：先命中再执行，委托 Celery 异步执行。

    步骤：
      1. run_ad_time_pricing_task.delay() —— 扫描新广告，匹配策略，写入命中记录
      2. run_time_pricing_task.apply_async(countdown=5) —— 5 秒后执行分时开始或回调

    使用 Redis 分布式锁保证同一时刻只有一个执行实例。
    Celery single_thread_queue（concurrency=1）保证两个任务顺序执行。
    """
    if not cache.add(_TIME_PRICING_LOCK_KEY, "1", timeout=1800):
        return Response({"code": "B0001", "data": None, "msg": "分时任务正在执行中"}, status=409)

    try:
        result1 = run_ad_time_pricing_task.delay()
        # 等待命中任务完成后再执行分时（5 秒后入队，给命中任务留出执行窗口）
        result2 = run_time_pricing_task.apply_async(countdown=5)
        return Response({
            "code": "00000",
            "data": {
                "ad_time_pricing_task_id": str(result1.id),
                "time_pricing_task_id": str(result2.id),
            },
            "msg": "分时任务已入队，将由 Celery 异步执行",
        })
    except Exception:
        cache.delete(_TIME_PRICING_LOCK_KEY)
        return Response({"code": "B0002", "data": None, "msg": "入队失败"}, status=500)
