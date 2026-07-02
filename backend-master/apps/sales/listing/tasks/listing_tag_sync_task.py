"""Listing 标签同步任务（listing_tag_sync_task）。

读取 LxListingTag 创建中/删除中的记录，调 middle.hanlis.cn API 完成同步。
运行在 single_thread_queue（concurrency=1），保证串行执行。
"""
import logging

from celery import shared_task

from apps.sales.listing.services.listing_tag_service import execute_listing_tag_sync
from api_v2.utils.task_execution_lock import TaskExecutionLock

logger = logging.getLogger(__name__)

# 任务执行锁：本任务仅由 Beat 触发，无 HTTP 视图，仅用于 Beat 高频触发去重
LOCK_KEY = "listing_tag_sync_lock"
# Beat 每 5 秒触发一次；任务 time_limit=900，TTL 取 960 兜底强杀场景
LOCK_TTL = 960


@shared_task(
    bind=True,
    name="api_v2.tasks.listing_tag_sync_task.run_listing_tag_sync_task",
    max_retries=0,
    soft_time_limit=840,
    time_limit=900,
    acks_late=True,
)
def run_listing_tag_sync_task(self) -> dict:
    """执行 Listing 标签同步：创建中标签调 addTag + 查询回写，删除中标签调 removeTag 并删除记录。"""
    with TaskExecutionLock(LOCK_KEY, ttl=LOCK_TTL) as acquired:
        if not acquired:
            logger.info("[run_listing_tag_sync_task] 上一次同步仍在执行，跳过本轮")
            return {"msg": "skipped, lock held"}

        result = execute_listing_tag_sync()
        logger.info(
            "[run_listing_tag_sync_task] 完成 creating=%s deleting=%s",
            result.get("creating"), result.get("deleting"),
        )
        return result
