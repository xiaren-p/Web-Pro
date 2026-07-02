"""广告分时策略——手动触发接口。

注意：此接口仅负责入队 Celery 任务并立即返回，避免在 gunicorn worker
      进程中同步执行重 DB / 重内存操作导致超时被 kill。

并发控制（"任务在跑就拒绝"语义）：
    视图调度前检查两条流水线任务的执行锁，任一被占即返回 409。
    锁占用 / 释放由任务本体的 ``TaskExecutionLock`` 负责，视图只读不写。
"""
import logging

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from apps.ads.sp.tasks.ad_time_pricing_task import (
    LOCK_KEY as AD_TIME_PRICING_LOCK_KEY,
    run_ad_time_pricing_task,
)
from apps.ads.sp.tasks.time_pricing_task import (
    LOCK_KEY as TIME_PRICING_LOCK_KEY,
    run_time_pricing_task,
)
from api_v2.utils.task_execution_lock import BUSY_RESPONSE, is_task_running

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_time_pricing(request: Request) -> Response:
    """分时策略一键执行：先策略命中匹配，再执行分时动作，委托 Celery 异步执行。

    执行链路：
      1. run_ad_time_pricing_task.delay() —— 扫描新广告，匹配策略，写入命中记录
      2. run_time_pricing_task.apply_async(countdown=5) —— 5 秒后执行分时开始或回调

    并发控制：
      - 调度前检查两条任务的执行锁，任一被占即返回 409
      - 锁的占用 / 释放由任务体 TaskExecutionLock 负责
      - Celery single_thread_queue（concurrency=1）保证两个任务严格顺序执行

    countdown=5 设计意图：
      两个 Task 均投递到同一 single_thread_queue（concurrency=1），
      Task 2 必然在 Task 1 完成后才执行。countdown=5 仅作为 broker 消息
      层面的保险：防止极端情况下消息乱序到达导致 Task 2 先于 Task 1 被 worker 拾取。

    Args:
        request: DRF Request 对象

    Returns:
        Response: 成功时 {"code": "00000", "data": {task_ids}, "msg": "..."}
                  并发冲突时 {"code": "B0001", ...} status=409
    """
    if is_task_running(AD_TIME_PRICING_LOCK_KEY):
        return Response(BUSY_RESPONSE("分时策略命中任务正在执行中"), status=409)
    if is_task_running(TIME_PRICING_LOCK_KEY):
        return Response(BUSY_RESPONSE("分时策略执行任务正在执行中"), status=409)

    result1 = None
    try:
        result1 = run_ad_time_pricing_task.delay()
        result2 = run_time_pricing_task.apply_async(countdown=5)
    except Exception:
        # Task 2 入队失败时，尝试撤销已入队的 Task 1，
        # 防止命中记录已更新但分时动作永不执行的不一致状态。
        logger.exception(
            "[trigger_time_pricing] Task 入队异常，尝试撤销 Task 1: task1=%s",
            result1.id if result1 else "N/A",
        )
        if result1 is not None:
            result1.revoke(terminate=False)
        return Response(
            {"code": "B0002", "data": None, "msg": "Celery 任务入队失败，请稍后重试"},
            status=500,
        )

    return Response({
        "code": "00000",
        "data": {
            "ad_time_pricing_task_id": str(result1.id),
            "time_pricing_task_id": str(result2.id),
        },
        "msg": "分时任务已入队，将由 Celery 异步执行",
    })
