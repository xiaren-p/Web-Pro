"""竞价调整任务（bid_adjustment_task）。

获取 SpBidAdjustment 待执行记录，调用 middle.hanlis.cn API 执行竞价调整。
运行在 single_thread_queue（concurrency=1），API 令牌桶=1 必须串行。
"""
import logging

from celery import shared_task

from api_v2.services.bid_adjustment_executor import execute_bid_adjustment
from api_v2.utils.task_execution_lock import TaskExecutionLock

logger = logging.getLogger(__name__)

# 任务执行锁：视图层调用 is_task_running(LOCK_KEY) 提前判断
LOCK_KEY = "bid_adjustment_lock"
LOCK_TTL = 960


@shared_task(
    bind=True,
    name="api_v2.tasks.bid_adjustment_task.run_bid_adjustment_task",
    max_retries=0,
    soft_time_limit=840,
    time_limit=900,
    acks_late=True,
)
def run_bid_adjustment_task(self) -> dict:
    """执行竞价调整 API 调用。"""
    with TaskExecutionLock(LOCK_KEY, ttl=LOCK_TTL) as acquired:
        if not acquired:
            logger.warning("[run_bid_adjustment_task] 任务已在执行中，跳过")
            return {"processed": 0, "success": 0, "failed": 0, "errors": ["任务已在执行中"]}

        logger.info("[run_bid_adjustment_task] 开始执行竞价调整")
        result = execute_bid_adjustment()
        logger.info(
            "[run_bid_adjustment_task] 完成: processed=%d success=%d failed=%d errors=%d",
            result["processed"], result["success"], result["failed"], len(result["errors"]),
        )
        return result
