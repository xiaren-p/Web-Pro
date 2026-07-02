"""SP 广告优化策略执行——手动触发接口。

支持全量执行和按维度单独执行，带参数级 Redis 锁防止同一维度并发调度。
"""
import logging

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth import BearerTokenAuthentication
from api_v2.permissions.workflow_permission import IsV2Accessible
from apps.ads.tasks.optimization_execution_task import (
    GLOBAL_LOCK_KEY,
    build_lock_key,
    run_optimization_execution_task,
)
from api_v2.utils.task_execution_lock import BUSY_RESPONSE, is_task_running

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]

# 合法维度列表
_VALID_DIMENSIONS = {
    "campaign", "targeting", "keyword", "product_targeting",
    "ad_group", "search_terms", "negative_targeting",
}


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def trigger_optimization_execution(request: Request) -> Response:
    """SP 广告优化策略执行——按维度调度或全量调度。

    请求体（JSON）：
      {
          "dimension": "campaign"  // 可选，不传则全量执行
                                    // 合法值: campaign / targeting / keyword /
                                    //        product_targeting / ad_group /
                                    //        search_terms / negative_targeting
      }

    并发控制：
      - 全量执行（不传 dimension）使用全局锁，同时只允许一个全量任务
      - 按维度执行使用参数级锁，同一维度不可并发，不同维度可并发
      - 全量执行时所有维度也禁止单独调度（视图层会显式检查全局锁）
      - 锁的占用 / 释放由任务体 ``TaskExecutionLock`` 负责，视图只读不写

    Args:
        request: DRF Request 对象

    Returns:
        Response: 成功时 {"code": "00000", "data": {"task_id": ..., "dimension": ...}, ...}
                  并发冲突时 {"code": "B0001", ...} status=409
    """
    dimension = (request.data or {}).get("dimension") if request.data else None

    # 校验维度
    if dimension is not None and dimension not in _VALID_DIMENSIONS:
        return Response(
            {
                "code": "B0003",
                "data": None,
                "msg": f"无效的维度: {dimension}，合法值: {sorted(_VALID_DIMENSIONS)}",
            },
            status=400,
        )

    # 全量任务在跑时，任何维度的单独调度也应被拒（避免覆盖全量正在处理的数据）
    if is_task_running(GLOBAL_LOCK_KEY):
        return Response(BUSY_RESPONSE("优化策略全量执行任务正在执行中"), status=409)

    # 检查目标维度（或全量）的执行锁
    target_lock_key = build_lock_key(dimension)
    if is_task_running(target_lock_key):
        msg = (
            f"维度「{dimension}」执行任务正在执行中"
            if dimension
            else "优化策略全量执行任务正在执行中"
        )
        return Response(BUSY_RESPONSE(msg), status=409)

    try:
        task = run_optimization_execution_task.delay(dimension=dimension)
    except Exception:
        logger.exception("[trigger_optimization_execution] Celery 入队失败")
        return Response(
            {"code": "B0002", "data": None, "msg": "Celery 任务入队失败，请稍后重试"},
            status=500,
        )

    return Response({
        "code": "00000",
        "data": {
            "task_id": str(task.id),
            "dimension": dimension or "all",
        },
        "msg": (
            f"维度「{dimension}」执行任务已入队" if dimension
            else "全量执行任务已入队"
        ),
    })
