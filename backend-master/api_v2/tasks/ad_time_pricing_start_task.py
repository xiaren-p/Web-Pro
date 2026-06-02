"""分时开始任务（ad_time_pricing_start_task）。

遍历 AdTimePricingHit 中待分时的记录，匹配时间区间并执行竞价调整。
运行在 single_thread_queue（concurrency=1），确保串行执行。
"""
import logging

from celery import shared_task

from api_v2.services.ad_rules.time_pricing_executor import execute_time_pricing_start

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="api_v2.tasks.ad_time_pricing_start_task.run_time_pricing_start_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def run_time_pricing_start_task(self) -> dict:
    """执行分时开始：匹配时间区间并计算调整竞价。

    Returns:
        {"processed": int, "adjusted": int, "errors": [str]}
    """
    logger.info("[run_time_pricing_start_task] 开始执行分时开始")
    result = execute_time_pricing_start()
    logger.info(
        "[run_time_pricing_start_task] 完成: processed=%d adjusted=%d errors=%d",
        result["processed"], result["adjusted"], len(result["errors"]),
    )
    return result
