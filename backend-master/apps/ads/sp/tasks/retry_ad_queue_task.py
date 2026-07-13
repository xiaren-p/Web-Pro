"""SP 广告上传队列失败记录每日自动重试 Celery 任务。

每天 18:00 由 Celery Beat 触发，将所有 FAILED / ANOMALY 状态
的广告上传队列记录重置为 PENDING，并链式触发提交任务立即处理。
"""
from __future__ import annotations

import logging

from celery import shared_task

from apps.ads.sp.rules.models.ad_upload_queue import AdParseStatus, AdUploadQueue
from apps.ads.sp.rules.tasks.ad_campaign_submit_task import (
    submit_pending_campaigns_task,
)
from apps.common.utils.task_execution_lock import TaskExecutionLock

logger = logging.getLogger(__name__)

LOCK_KEY = "retry_ad_queue_lock"
LOCK_TTL = 120  # >= time_limit(60) + 60


@shared_task(
    bind=True,
    name="apps.ads.sp.tasks.retry_ad_queue_task.retry_failed_ad_queue_task",
    max_retries=0,
    soft_time_limit=55,
    time_limit=60,
    acks_late=True,
)
def retry_failed_ad_queue_task(self) -> dict:
    """将所有 FAILED 和 ANOMALY 状态的广告上传队列记录重置为 PENDING。

    加 TaskExecutionLock 防止并发执行。
    重置后链式调用 submit_pending_campaigns_task 立即处理。
    """

    with TaskExecutionLock(LOCK_KEY, ttl=LOCK_TTL):
        retried = AdUploadQueue.objects.filter(
            parse_status__in=[AdParseStatus.FAILED, AdParseStatus.ANOMALY]
        ).update(
            parse_status=AdParseStatus.PENDING,
            msg="队列中",
        )

        logger.info("[retry_failed_ad_queue_task] 已重置 %s 条记录为 PENDING", retried)

        if retried > 0:
            submit_pending_campaigns_task.delay()
            logger.info("[retry_failed_ad_queue_task] 已触发提交任务")

    return {"retried_count": retried}
