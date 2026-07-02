"""SP 广告优化策略执行任务（optimization_execution_task）。

扫描 SpAdOptimizationStrategy 中已命中的规则，支持全量执行和按维度单独执行。

并发控制（与 optimization_execution_view 共用同一套锁）：
    - 全量执行（dimension=None）使用全局锁 ``GLOBAL_LOCK_KEY``
    - 按维度执行使用 ``DIM_LOCK_PREFIX + dimension`` 维度级锁
    - 视图层调用 ``is_task_running(build_lock_key(dim))`` 提前判断
"""
import logging

from celery import shared_task

from apps.ads.sp.rules.services.ad_optimization.execution_service import (
    execute_all_dimensions,
    execute_single_dimension,
)
from api_v2.utils.task_execution_lock import TaskExecutionLock

logger = logging.getLogger(__name__)

# 全量执行锁：视图传 dimension=None 时用
GLOBAL_LOCK_KEY = "sp_ad_optimization_execution_lock"
# 维度级锁前缀：实际 key = DIM_LOCK_PREFIX + dimension
DIM_LOCK_PREFIX = "sp_ad_optimization_execution_dim:"
LOCK_TTL = 1860


def build_lock_key(dimension: str | None) -> str:
    """根据维度参数构造对应锁 key。

    Args:
        dimension (str | None): 维度名；为 None 表示全量执行。

    Returns:
        str: 对应的 Redis 锁 key。
    """
    if dimension is None:
        return GLOBAL_LOCK_KEY
    return DIM_LOCK_PREFIX + dimension


@shared_task(
    bind=True,
    name="apps.ads.sp.rules.tasks.optimization_execution_task.run_optimization_execution_task",
    max_retries=0,
    soft_time_limit=1620,
    time_limit=1800,
    acks_late=True,
)
def run_optimization_execution_task(self, dimension: str | None = None) -> dict:
    """执行 SP 广告优化策略规则（全量或按维度）。

    由 Celery Beat 定时调用或通过 API 手动触发。
    运行在 single_thread_queue（concurrency=1）。

    Args:
        dimension: 维度名称。为 None 时执行全部维度；非 None 时执行单个维度。
                   合法值：campaign / targeting / keyword / product_targeting
                          / ad_group / search_terms / negative_targeting

    Returns:
        dict: 执行结果汇总
    """
    lock_key = build_lock_key(dimension)
    with TaskExecutionLock(lock_key, ttl=LOCK_TTL) as acquired:
        if not acquired:
            logger.warning(
                "[run_optimization_execution_task] 锁被占跳过: dim=%s key=%s",
                dimension or "<all>",
                lock_key,
            )
            return {"skipped": True, "dimension": dimension or "all", "errors": ["任务已在执行中"]}

        if dimension:
            logger.info("[run_optimization_execution_task] 开始执行维度: %s", dimension)
            result = execute_single_dimension(dimension)
            logger.info(
                "[run_optimization_execution_task] 完成维度 %s: executed=%d",
                dimension,
                result.get("执行规则数", result.get("executed", 0)),
            )
        else:
            logger.info("[run_optimization_execution_task] 开始执行全维度优化策略规则")
            result = execute_all_dimensions()
            logger.info(
                "[run_optimization_execution_task] 完成全维度: campaign=%d",
                result.get("campaign", {}).get("executed", 0),
            )
        return result
