"""竞价调整——手动触发接口。"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.tasks.bid_adjustment_task import run_bid_adjustment_task


@api_view(["POST"])
@authentication_classes([BearerTokenAuthentication])
@permission_classes([])
def trigger_bid_adjustment(request: Request) -> Response:
    """手动触发竞价调整任务（异步 Celery 执行）。"""
    task = run_bid_adjustment_task.delay()
    return Response({
        "code": "00000",
        "data": {"task_id": task.id, "message": "竞价调整任务已入队"},
        "msg": "success",
    })
