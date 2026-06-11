"""SP 广告优化策略匹配任务（optimization_strategy_task）。

Celery 定时 / 手动触发调用，扫描所有开启的 SP 广告活动，匹配 LxAdRule 优化策略
规则，写入 SpAdOptimizationStrategy 记录。

注意：该任务必须串行执行（single_thread_queue，concurrency=1），
      防止并发写入 SpAdOptimizationStrategy 导致重复记录。
"""
import logging

from celery import shared_task

from api_v2.services.ad_optimization.optimization_strategy_service import (
    process_optimization_strategies,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="api_v2.tasks.optimization_strategy_task.run_optimization_strategy_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def run_optimization_strategy_task(self) -> dict:
    """扫描 SP 广告活动并匹配优化策略规则。

    由 Celery Beat 定时调用或通过 API 手动触发。
    运行在 single_thread_queue（concurrency=1），Celery 层面保证不并行。

    Returns:
        dict: {"total_campaigns", "matched", "written", "new_records",
               "updated_records", "errors"}
    """
    logger.info("[run_optimization_strategy_task] 开始扫描 SP 广告优化策略")
    result = process_optimization_strategies()
    logger.info(
        "[run_optimization_strategy_task] 完成: total=%d, matched=%d, "
        "written=%d（new=%d, updated=%d）, errors=%d",
        result["total_campaigns"],
        result["matched"],
        result["written"],
        result["new_records"],
        result["updated_records"],
        len(result["errors"]),
    )
    return result
