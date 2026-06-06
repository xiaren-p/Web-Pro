"""广告分时策略——手动触发接口。"""
from django.core.cache import cache
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.services.ad_rules.ad_time_pricing_service import process_new_ads
from api_v2.services.ad_rules.time_pricing_service import execute_time_pricing

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]

_TIME_PRICING_LOCK_KEY = "time_pricing_lock"


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_time_pricing(request: Request) -> Response:
    """分时策略一键执行：先命中再执行，合并为一个 API。

    步骤：
      1. process_new_ads()   —— 扫描新广告，匹配策略，写入命中记录
      2. execute_time_pricing() —— 根据命中记录的 is_callback/时段状态执行分时开始或回调

    使用 Redis 分布式锁保证同一时刻只有一个执行实例。
    """
    if cache.add(_TIME_PRICING_LOCK_KEY, "1", timeout=1800):
        try:
            result1 = process_new_ads()
            result2 = execute_time_pricing()
            return Response({
                "code": "00000",
                "data": {
                    "ad_time_pricing": result1,
                    "time_pricing_execute": result2,
                },
                "msg": "success",
            })
        finally:
            cache.delete(_TIME_PRICING_LOCK_KEY)
    return Response({"code": "B0001", "data": None, "msg": "分时任务正在执行中"}, status=409)
