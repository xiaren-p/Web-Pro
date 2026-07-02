"""Listing 商品标签修改任务（listing_tag_modify_task）。

读取 ListingTagModifyQueue 新增/移除记录，调 middle.hanlis.cn API 完成标签绑定同步。
运行在 single_thread_queue（concurrency=1），保证串行执行。
"""
import logging

from celery import shared_task

from apps.sales.listing.services.listing_tag_modify_service import execute_listing_tag_modify
from apps.common.utils.task_execution_lock import TaskExecutionLock

logger = logging.getLogger(__name__)

# 任务执行锁：本任务仅由 Beat 触发，无 HTTP 视图，仅用于 Beat 高频触发去重
LOCK_KEY = "listing_tag_modify_lock"
# Beat 每 5 秒触发一次；任务 time_limit=900，TTL 取 960 兜底强杀场景
LOCK_TTL = 960


@shared_task(
    bind=True,
    name="api_v2.tasks.listing_tag_modify_task.run_listing_tag_modify_task",
    max_retries=0,
    soft_time_limit=840,
    time_limit=900,
    acks_late=True,
)
def run_listing_tag_modify_task(self) -> dict:
    """执行 Listing 商品标签修改同步：新增 bindListingAndTag，移除 removeListingAndTag。"""
    with TaskExecutionLock(LOCK_KEY, ttl=LOCK_TTL) as acquired:
        if not acquired:
            logger.info("[run_listing_tag_modify_task] 上一次同步仍在执行，跳过本轮")
            return {"msg": "skipped, lock held"}

        result = execute_listing_tag_modify()
        logger.info(
            "[run_listing_tag_modify_task] 完成 add=%s remove=%s",
            result.get("add"), result.get("remove"),
        )
        return result
