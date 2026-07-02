"""广告活动参考数据缓存刷新任务（listing_cache_refresh_task）。

定期预热 Redis 中的参考数据缓存（profile/shop/rate/tag/owner/asin），
保证页面请求直接命中 Redis，避免首个请求触发冷加载全表扫描。
运行在默认 celery 队列（轻量任务，无需单线程保护）。
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.ads.sp.tasks.listing_cache_refresh_task.refresh_listing_caches",
    max_retries=0,
    soft_time_limit=30,
    time_limit=60,
)
def refresh_listing_caches(self) -> dict:
    """定时刷新所有参考数据缓存 + 标签/负责人 ASIN 映射缓存。

    Returns:
        dict: 执行摘要。
    """
    from api_v1.views.lingxing.ads.sp.ad_campaign_view import (
        _get_profile_map,
        _get_rate_map,
        _get_sid_country_map,
        _load_all_listing_caches,
    )

    logger.info("[refresh_listing_caches] 开始刷新参考数据缓存")
    try:
        _load_all_listing_caches()
        _get_profile_map()
        _get_sid_country_map()
        _get_rate_map()
        logger.info("[refresh_listing_caches] 刷新完成")
        return {"status": "ok"}
    except Exception as exc:
        logger.exception("[refresh_listing_caches] 刷新失败: %s", exc)
        return {"status": "error", "error": str(exc)}
