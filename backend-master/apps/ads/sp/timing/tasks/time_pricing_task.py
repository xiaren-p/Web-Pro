"""分时任务（time_pricing_task）。

合并原 start / callback 两个 Celery 任务为一个。
"""
import logging

from celery import shared_task

from apps.ads.sp.timing.services.time_pricing_service import execute_time_pricing
from apps.common.utils.task_execution_lock import TaskExecutionLock

logger = logging.getLogger(__name__)

# 任务执行锁：视图层调用 is_task_running(LOCK_KEY) 提前判断
LOCK_KEY = "time_pricing_task_lock"
LOCK_TTL = 1860


@shared_task(
    bind=True,
    name="apps.ads.sp.timing.tasks.time_pricing_task.run_time_pricing_task",
    max_retries=0,
    soft_time_limit=1620,
    time_limit=1800,
    acks_late=True,
)
def run_time_pricing_task(self) -> dict:
    """执行分时：根据时段判断开始或回调。

    由 Celery Beat 定时调用或通过 API 手动触发。

    Returns:
        dict: {"processed", "adjusted", "errors"}
    """
    with TaskExecutionLock(LOCK_KEY, ttl=LOCK_TTL) as acquired:
        if not acquired:
            logger.warning("[run_time_pricing_task] 任务已在执行中，跳过")
            return {"processed": 0, "adjusted": 0, "errors": ["任务已在执行中"]}

        logger.info("[run_time_pricing_task] 开始执行分时策略")
        result = execute_time_pricing()
        logger.info(
            "[run_time_pricing_task] 完成: processed=%d adjusted=%d errors=%d",
            result["processed"], result["adjusted"], len(result["errors"]),
        )
        return result
