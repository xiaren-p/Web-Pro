"""图片同步队列监控任务（image_sync_queue_task）。

Beat 定时扫描 ImageSyncQueue 中 PENDING 状态的记录，
从 NC 下载图片并调领星 API 完成 listing 图片上传/更新。
运行在 single_thread_queue（concurrency=1），保证串行执行。
"""
import logging

from celery import shared_task

from api_v2.services.image_sync_service import execute_image_sync
from api_v2.utils.task_execution_lock import TaskExecutionLock

logger = logging.getLogger(__name__)

# 任务执行锁：本任务仅由 Beat 触发，无 HTTP 视图，仅用于 Beat 高频触发去重
LOCK_KEY = "image_sync_queue_lock"
# Beat 每 30 秒触发一次；任务 time_limit=900，TTL 取 960 兜底强杀场景
LOCK_TTL = 960


@shared_task(
    bind=True,
    name="api_v2.tasks.image_sync_queue_task.run_image_sync_queue_task",
    max_retries=0,
    soft_time_limit=840,
    time_limit=900,
    acks_late=True,
)
def run_image_sync_queue_task(self) -> dict:
    """执行图片同步队列监控：扫描 PENDING 记录，下载 NC 图片，调领星 API 更新 listing。

    Returns:
        dict: 处理汇总，含 processed / success / failed / errors 字段。
    """
    with TaskExecutionLock(LOCK_KEY, ttl=LOCK_TTL) as acquired:
        if not acquired:
            logger.info("[run_image_sync_queue_task] 上一次同步仍在执行，跳过本轮")
            return {"msg": "skipped, lock held"}

        result = execute_image_sync()
        logger.info(
            "[run_image_sync_queue_task] 完成 processed=%s success=%s failed=%s",
            result.get("processed"), result.get("success"), result.get("failed"),
        )
        return result
