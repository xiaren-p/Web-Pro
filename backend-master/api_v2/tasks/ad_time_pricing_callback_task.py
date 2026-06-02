"""分时回调任务（ad_time_pricing_callback_task）。

遍历正在分时的记录，离开时段后执行回调恢复竞价。
运行在 single_thread_queue（concurrency=1）。
"""
import logging

from celery import shared_task
from django.core.cache import cache

from api_v2.services.ad_rules.time_pricing_callback import execute_time_pricing_callback

logger = logging.getLogger(__name__)

_CALLBACK_LOCK_KEY = "ad_time_pricing_callback_lock"


@shared_task(
    bind=True,
    name="api_v2.tasks.ad_time_pricing_callback_task.run_time_pricing_callback_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def run_time_pricing_callback_task(self) -> dict:
    """执行分时回调：离开时段后恢复竞价。"""
    logger.info("[run_time_pricing_callback_task] 开始执行分时回调")
    try:
        result = execute_time_pricing_callback()
        logger.info(
            "[run_time_pricing_callback_task] 完成: processed=%d called_back=%d errors=%d",
            result["processed"], result["called_back"], len(result["errors"]),
        )
        return result
    finally:
        cache.delete(_CALLBACK_LOCK_KEY)
