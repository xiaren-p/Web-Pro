"""分时任务（time_pricing_task）。

合并原 start / callback 两个 Celery 任务为一个。
"""
import logging

from celery import shared_task

from api_v2.services.ad_rules.time_pricing_service import execute_time_pricing

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="api_v2.tasks.time_pricing_task.run_time_pricing_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def run_time_pricing_task(self) -> dict:
    """执行分时：根据时段判断开始或回调。"""
    logger.info("[run_time_pricing_task] 开始执行分时策略")
    result = execute_time_pricing()
    logger.info(
        "[run_time_pricing_task] 完成: processed=%d adjusted=%d errors=%d",
        result["processed"], result["adjusted"], len(result["errors"]),
    )
    return result
