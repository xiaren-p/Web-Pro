"""SP 广告优化策略执行任务（optimization_execution_task）。

扫描 SpAdOptimizationStrategy 中已命中的规则，按维度执行操作。
"""
import logging

from celery import shared_task

from api_v2.services.ad_optimization.execution_service import execute_all_dimensions

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="api_v2.tasks.optimization_execution_task.run_optimization_execution_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def run_optimization_execution_task(self) -> dict:
    """执行 SP 广告优化策略规则。

    由 Celery Beat 定时调用或通过 API 手动触发。
    运行在 single_thread_queue（concurrency=1）。

    Returns:
        dict: 各维度的执行结果汇总
    """
    logger.info("[run_optimization_execution_task] 开始执行优化策略规则")
    result = execute_all_dimensions()
    logger.info(
        "[run_optimization_execution_task] 完成: campaign=%d",
        result["campaign"].get("executed", 0),
    )
    return result
