"""投放实体调整历史查询视图。"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from apps.system.auth import BearerTokenAuthentication
from apps.system.permissions.api_access import IsApiAccessible
from apps.ads.sp.selectors.adjustment_history_selector import (
    query_campaign_adjustment_history,
    query_entity_adjustment_history,
)
from apps.common.utils.responses import drf_error, drf_ok

_AUTH = [BearerTokenAuthentication]
_PERM = [IsApiAccessible]


@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def get_adjustment_history(request: Request) -> Response:
    """查询投放实体或广告活动的调整历史。

    Query params:
        keyword_id: int  (三选一)
        target_id:   int
        campaign_id: int
        profile_id:  int  (必填)
        days:        int  (可选，默认 90)
    """
    profile_id = request.query_params.get("profile_id")
    if not profile_id:
        return drf_error("profile_id 为必填参数", code="B0001")

    days = int(request.query_params.get("days", 90))

    keyword_id = request.query_params.get("keyword_id")
    target_id = request.query_params.get("target_id")
    campaign_id = request.query_params.get("campaign_id")

    if keyword_id:
        records = query_entity_adjustment_history(
            "keyword", int(keyword_id), int(profile_id), days,
        )
    elif target_id:
        records = query_entity_adjustment_history(
            "target", int(target_id), int(profile_id), days,
        )
    elif campaign_id:
        records = query_campaign_adjustment_history(
            int(campaign_id), int(profile_id), days,
        )
    else:
        return drf_error("keyword_id / target_id / campaign_id 三选一必填", code="B0001")

    return drf_ok({"total": len(records), "records": records})
