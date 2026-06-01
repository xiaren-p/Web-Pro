"""广告活动队列监控与提交 Celery 任务（ad_campaign_submit_task，运行于并行队列）。

定时扫描 AdUploadQueue 中 parse_status=SUCCESS 且 campaign_status=PENDING 的记录，
逐条向领星广告接口提交广告活动创建请求。
"""

import logging

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

# 与 ad_campaign_submit_view 共用同一把互斥锁，防止 Celery 与 HTTP 接口并发执行
_LOCK_KEY = "ad_campaign_submit_running"
_LOCK_TTL = 300


@shared_task(
    bind=True,
    name='api_v2.tasks.ad_campaign_submit_task.submit_pending_campaigns_task',
    max_retries=0,
    soft_time_limit=120,
    time_limit=180,
)
def submit_pending_campaigns_task(self) -> dict:
    """扫描并提交待创建的广告活动。

    从 AdUploadQueue 中取出 parse_status=1(SUCCESS) 且 campaign_status=0(PENDING)
    的记录，调用领星广告接口批量创建广告活动，并将结果回写至队列记录。

    Returns:
        dict: 执行结果摘要，含 total / submitted / failed 字段。
    """
    logger.info("[submit_pending_campaigns_task] 任务启动")

    # 与 HTTP 接口共用互斥锁，防止 Celery 任务与手动触发并发执行同一批队列记录
    acquired = cache.add(_LOCK_KEY, True, timeout=_LOCK_TTL)
    if not acquired:
        logger.warning("[submit_pending_campaigns_task] 互斥锁已被占用，跳过本次执行")
        return {"total": 0, "submitted": 0, "failed": 0, "skipped": True}

    try:
        from api_v2.services.ad_creation.ad_campaign_submit_service import process_pending_campaigns
        result = process_pending_campaigns()
    except Exception as exc:
        logger.error(
            "[submit_pending_campaigns_task] 任务执行异常: %s",
            exc,
            exc_info=True,
        )
        return {"total": 0, "submitted": 0, "failed": 0, "error": str(exc)}
    finally:
        cache.delete(_LOCK_KEY)

    logger.info(
        "[submit_pending_campaigns_task] 任务完成: total=%s submitted=%s failed=%s",
        result.get("total"),
        result.get("submitted"),
        result.get("failed"),
    )
    return result
