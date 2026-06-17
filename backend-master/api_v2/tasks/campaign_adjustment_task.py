"""广告活动调整任务（campaign_adjustment_task）。

获取 SpCampaignAdjustment 待执行记录，调用 middle.hanlis.cn API 执行预算调整/暂停。
运行在 single_thread_queue（concurrency=1），API 令牌桶=1 必须串行。
"""
import logging

from celery import shared_task
from django.core.cache import cache

from api_v2.services.campaign_adjustment_executor import execute_campaign_adjustment

logger = logging.getLogger(__name__)

_CAMPAIGN_ADJUST_LOCK_KEY = "campaign_adjustment_lock"


@shared_task(
    bind=True,
    name="api_v2.tasks.campaign_adjustment_task.run_campaign_adjustment_task",
    max_retries=0,
    soft_time_limit=1200,
    time_limit=1800,
)
def run_campaign_adjustment_task(self) -> dict:
    """执行广告活动调整 API 调用。"""
    logger.info("[run_campaign_adjustment_task] 开始执行广告活动调整")
    try:
        result = execute_campaign_adjustment()
        logger.info(
            "[run_campaign_adjustment_task] 完成: processed=%d success=%d failed=%d errors=%d",
            result["processed"], result["success"], result["failed"], len(result["errors"]),
        )
        return result
    finally:
        cache.delete(_CAMPAIGN_ADJUST_LOCK_KEY)
