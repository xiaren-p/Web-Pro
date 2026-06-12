"""SP 广告优化策略执行任务（optimization_execution_task）。

扫描 SpAdOptimizationStrategy 中已命中的规则，支持全量执行和按维度单独执行。
"""
import logging

from celery import shared_task

from api_v2.services.ad_optimization.execution_service import (
    execute_all_dimensions,
    execute_single_dimension,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="api_v2.tasks.optimization_execution_task.run_optimization_execution_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
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
