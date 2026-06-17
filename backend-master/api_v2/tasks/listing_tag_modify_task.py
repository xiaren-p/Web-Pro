"""Listing 商品标签修改任务（listing_tag_modify_task）。

读取 ListingTagModifyQueue 新增/移除记录，调 middle.hanlis.cn API 完成标签绑定同步。
运行在 single_thread_queue（concurrency=1），保证串行执行。
"""
import logging

from celery import shared_task
from django.core.cache import cache

from api_v2.services.listing_tag_modify_service import execute_listing_tag_modify

logger = logging.getLogger(__name__)

_LISTING_TAG_MODIFY_LOCK_KEY = "listing_tag_modify_lock"


@shared_task(
    bind=True,
    name="api_v2.tasks.listing_tag_modify_task.run_listing_tag_modify_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def run_listing_tag_modify_task(self) -> dict:
    """执行 Listing 商品标签修改同步：新增 bindListingAndTag，移除 removeListingAndTag。"""
    logger.info("[run_listing_tag_modify_task] 尝试获取分布式锁")

    if not cache.add(_LISTING_TAG_MODIFY_LOCK_KEY, "1", timeout=600):
        logger.info("[run_listing_tag_modify_task] 上一次同步仍在执行，跳过本轮")
        return {"msg": "skipped, lock held"}

    try:
        result = execute_listing_tag_modify()
        logger.info(
            "[run_listing_tag_modify_task] 完成 add=%s remove=%s",
            result.get("add"), result.get("remove"),
        )
        return result
    finally:
        cache.delete(_LISTING_TAG_MODIFY_LOCK_KEY)
