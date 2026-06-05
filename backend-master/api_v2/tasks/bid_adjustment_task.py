"""竞价调整任务（bid_adjustment_task）。

获取 SpBidAdjustment 待执行记录，调用 middle.hanlis.cn API 执行竞价调整。
运行在 single_thread_queue（concurrency=1），API 令牌桶=1 必须串行。
"""
import logging

from celery import shared_task
from django.core.cache import cache

from api_v2.services.bid_adjustment_executor import execute_bid_adjustment

logger = logging.getLogger(__name__)

_BID_ADJUST_LOCK_KEY = "bid_adjustment_lock"


@shared_task(
    bind=True,
    name="api_v2.tasks.bid_adjustment_task.run_bid_adjustment_task",
    max_retries=0,
    soft_time_limit=1200,
    time_limit=1800,
)
def run_bid_adjustment_task(self) -> dict:
    """执行竞价调整 API 调用。"""
    logger.info("[run_bid_adjustment_task] 开始执行竞价调整")
    try:
        result = execute_bid_adjustment()
        logger.info(
            "[run_bid_adjustment_task] 完成: processed=%d success=%d failed=%d errors=%d",
            result["processed"], result["success"], result["failed"], len(result["errors"]),
        )
        return result
    finally:
        cache.delete(_BID_ADJUST_LOCK_KEY)
