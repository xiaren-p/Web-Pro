"""广告分时策略——手动触发接口。"""
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

_AD_TIME_PRICING_LOCK_KEY = "ad_time_pricing_task_lock"
_AD_TIME_PRICING_LOCK_TTL = 1500

_TIME_PRICING_LOCK_KEY = "time_pricing_lock"
_TIME_PRICING_LOCK_TTL = 1800


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_ad_time_pricing(request: Request) -> Response:
    """手动触发分时策略命中任务。"""
    if cache.get(_AD_TIME_PRICING_LOCK_KEY):
        return Response({"code": "B0001", "data": None, "msg": "分时策略命中任务正在执行中"}, status=409)
    cache.set(_AD_TIME_PRICING_LOCK_KEY, "1", timeout=_AD_TIME_PRICING_LOCK_TTL)
    task = run_ad_time_pricing_task.delay()
    return Response({"code": "00000", "data": {"task_id": task.id, "message": "分时策略命中任务已入队"}, "msg": "success"})


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_time_pricing(request: Request) -> Response:
    """手动触发分时执行任务（合并 start + callback）。"""
    if cache.get(_TIME_PRICING_LOCK_KEY):
        return Response({"code": "B0001", "data": None, "msg": "分时任务正在执行中"}, status=409)
    cache.set(_TIME_PRICING_LOCK_KEY, "1", timeout=_TIME_PRICING_LOCK_TTL)
    task = run_time_pricing_task.delay()
    return Response({"code": "00000", "data": {"task_id": task.id, "message": "分时任务已入队"}, "msg": "success"})


@api_view(["DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def unlock_ad_time_pricing(request: Request) -> Response:
    """强制清除分时策略任务锁。"""
    cache.delete(_AD_TIME_PRICING_LOCK_KEY)
    return Response({"code": "00000", "data": None, "msg": "锁已清除"})
