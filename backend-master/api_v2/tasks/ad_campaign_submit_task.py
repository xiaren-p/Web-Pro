"""广告活动队列监控与提交 Celery 任务（ad_campaign_submit_task，运行于并行队列）。

定时扫描 AdUploadQueue 中 parse_status=SUCCESS 且 campaign_status=PENDING 的记录，
逐条向领星广告接口提交广告活动创建请求。
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='api_v2.tasks.ad_campaign_submit_task.submit_pending_campaigns_task',
    queue='parallel_queue',
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

    try:
        from api_v2.services.ad_campaign_submit_service import process_pending_campaigns
        result = process_pending_campaigns()
    except Exception as exc:
        logger.error(
            "[submit_pending_campaigns_task] 任务执行异常: %s",
            exc,
            exc_info=True,
        )
        return {"total": 0, "submitted": 0, "failed": 0, "error": str(exc)}

    logger.info(
        "[submit_pending_campaigns_task] 任务完成: total=%s submitted=%s failed=%s",
        result.get("total"),
        result.get("submitted"),
        result.get("failed"),
    )
    return result
