"""广告分时策略命中——手动触发接口。"""
from django.core.cache import cache
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.tasks.ad_time_pricing_callback_task import run_time_pricing_callback_task
from api_v2.tasks.ad_time_pricing_start_task import run_time_pricing_start_task
from api_v2.tasks.ad_time_pricing_task import run_ad_time_pricing_task

# 互斥锁 cache key：确保同一时间只有一个分时策略命中任务在执行
_AD_TIME_PRICING_LOCK_KEY = "ad_time_pricing_task_lock"
_AD_TIME_PRICING_LOCK_TTL = 1500  # 15 分钟，与任务 time_limit 一致


@api_view(["POST"])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([])
def trigger_ad_time_pricing(request: Request) -> Response:
    """手动触发分时策略命中任务（异步 Celery 执行）。

    防重入：若已有任务正在执行（cache 锁存在），返回 409 Conflict。

    任务运行在 single_thread_queue（concurrency=1），确保 Celery 层面也不会并行。
    """
    if cache.get(_AD_TIME_PRICING_LOCK_KEY):
        return Response({
            "code": "B0001",
            "data": None,
            "msg": "分时策略命中任务正在执行中，请稍后再试",
        }, status=409)

    # 先加锁，再入队（避免竞态窗口）
    cache.set(_AD_TIME_PRICING_LOCK_KEY, "1", timeout=_AD_TIME_PRICING_LOCK_TTL)
    task = run_ad_time_pricing_task.delay()

    return Response({
        "code": "00000",
        "data": {"task_id": task.id, "message": "分时策略命中任务已入队"},
        "msg": "success",
    })


# 分时开始 / 回调任务的互斥锁
_START_LOCK_KEY = "ad_time_pricing_start_lock"
_CALLBACK_LOCK_KEY = "ad_time_pricing_callback_lock"
_TASK_LOCK_TTL = 1800


@api_view(["POST"])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([])
def trigger_time_pricing_start(request: Request) -> Response:
    """手动触发"分时开始"任务（异步 Celery 执行）。"""
    if cache.get(_START_LOCK_KEY):
        return Response({"code": "B0001", "data": None, "msg": "分时开始任务正在执行中"}, status=409)
    cache.set(_START_LOCK_KEY, "1", timeout=_TASK_LOCK_TTL)
    task = run_time_pricing_start_task.delay()
    return Response({"code": "00000", "data": {"task_id": task.id, "message": "分时开始任务已入队"}, "msg": "success"})


@api_view(["POST"])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([])
def trigger_time_pricing_callback(request: Request) -> Response:
    """手动触发"分时回调"任务（异步 Celery 执行）。"""
    if cache.get(_CALLBACK_LOCK_KEY):
        return Response({"code": "B0001", "data": None, "msg": "分时回调任务正在执行中"}, status=409)
    cache.set(_CALLBACK_LOCK_KEY, "1", timeout=_TASK_LOCK_TTL)
    task = run_time_pricing_callback_task.delay()
    return Response({"code": "00000", "data": {"task_id": task.id, "message": "分时回调任务已入队"}, "msg": "success"})


@api_view(["DELETE"])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([])
def unlock_ad_time_pricing(request: Request) -> Response:
    """强制清除分时策略任务锁（紧急情况下使用）。"""
    cache.delete(_AD_TIME_PRICING_LOCK_KEY)
    return Response({
        "code": "00000",
        "data": None,
        "msg": "锁已清除，可以重新触发任务",
    })
