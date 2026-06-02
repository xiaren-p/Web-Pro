"""广告分时策略命中任务（ad_time_pricing_task）。

Celery 定时 / 手动触发调用，扫描新广告并匹配分时策略规则。

注意：该任务必须串行执行（single_thread_queue，concurrency=1），
      防止并发写入 AdTimePricingHit 导致重复记录。
"""
import logging

from celery import shared_task

from api_v2.services.ad_rules.ad_time_pricing_service import process_new_ads

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="api_v2.tasks.ad_time_pricing_task.run_ad_time_pricing_task",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def run_ad_time_pricing_task(self) -> dict:
    """扫描新广告并匹配分时策略规则。

    由 Celery Beat 定时调用或通过 API 手动触发。
    必须运行在 single_thread_queue 中，确保上次执行完毕后才启动下一次。

    Returns:
        dict: {"total_campaigns", "new_ads_processed", "hits", "errors"}
    """
    logger.info("[run_ad_time_pricing_task] 开始扫描新广告并匹配分时策略")
    result = process_new_ads()
    logger.info(
        "[run_ad_time_pricing_task] 完成: total=%d, new=%d, hits=%d, errors=%d",
        result["total_campaigns"],
        result["new_ads_processed"],
        result["hits"],
        len(result["errors"]),
    )
    return result
