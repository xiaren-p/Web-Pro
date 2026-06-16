"""Listing 标签同步任务（listing_tag_sync_task）。

读取 LxListingTag 创建中/删除中的记录，调 middle.hanlis.cn API 完成同步。
运行在 single_thread_queue（concurrency=1），保证串行执行。
"""
import logging

from celery import shared_task
from django.core.cache import cache

from api_v2.services.listing_tag_service import execute_listing_tag_sync

logger = logging.getLogger(__name__)

_LISTING_TAG_SYNC_LOCK_KEY = "listing_tag_sync_lock"


@shared_task(
    bind=True,
    name="api_v2.tasks.listing_tag_sync_task.run_listing_tag_sync_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def run_listing_tag_sync_task(self) -> dict:
    """执行 Listing 标签同步：创建中标签调 addTag + 查询回写，删除中标签调 removeTag 并删除记录。"""
    logger.info("[run_listing_tag_sync_task] 尝试获取分布式锁")

    if not cache.add(_LISTING_TAG_SYNC_LOCK_KEY, "1", timeout=600):
        logger.info("[run_listing_tag_sync_task] 上一次同步仍在执行，跳过本轮")
        return {"msg": "skipped, lock held"}

    try:
        result = execute_listing_tag_sync()
        logger.info(
            "[run_listing_tag_sync_task] 完成 creating=%s deleting=%s",
            result.get("creating"), result.get("deleting"),
        )
        return result
    finally:
        cache.delete(_LISTING_TAG_SYNC_LOCK_KEY)
