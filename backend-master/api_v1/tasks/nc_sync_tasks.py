"""Nextcloud 同步 Celery 任务（nc_sync_tasks）。

Task 职责：
- process_pending_nc_tasks：批量消费 NcSyncTask 队列中 PENDING 状态的任务。
- retry_failed_nc_tasks：对 FAILED 且 retry_count < MAX_RETRIES 的任务再次尝试。

Celery Beat 推荐配置（在 settings.py 中追加 CELERY_BEAT_SCHEDULE）：
    'nc-process-pending': 每 30 秒执行一次 process_pending_nc_tasks
    'nc-retry-failed':    每 5  分钟执行一次 retry_failed_nc_tasks
"""
import logging
import time

from celery import shared_task

from api_v1.models.nc.nc_sync_task import NcSyncTask, SyncStatus
from api_v1.services.nc.nc_sync_service import NcSyncService

logger = logging.getLogger(__name__)

# 单批最大处理任务数，防止单次任务执行时间过长
_BATCH_SIZE = 50
# 每条任务执行后的间隔秒数，防止触发 Nextcloud 暴力破解限速（429）
_REQUEST_INTERVAL = 0.5


@shared_task(
    name="api_v1.tasks.nc_sync_tasks.process_pending_nc_tasks",
    bind=True,
    max_retries=0,
    soft_time_limit=120,
    time_limit=150,
)
def process_pending_nc_tasks(self) -> dict:
    """处理 NcSyncTask 队列中所有 PENDING 状态的任务（每批最多 _BATCH_SIZE 条）。

    Returns:
        dict: 执行摘要，包含 total/success/failed 计数。
    """
    tasks = list(
        NcSyncTask.objects.filter(status=SyncStatus.PENDING)
        .order_by("id")[:_BATCH_SIZE]
    )
    total = len(tasks)
    success = 0
    failed = 0
    for task in tasks:
        ok = NcSyncService.execute_task(task)
        if ok:
            success += 1
        else:
            failed += 1
        time.sleep(_REQUEST_INTERVAL)
    logger.info(
        "[nc_sync_tasks][process_pending] total=%s success=%s failed=%s",
        total, success, failed,
    )
    return {"total": total, "success": success, "failed": failed}


@shared_task(
    name="api_v1.tasks.nc_sync_tasks.retry_failed_nc_tasks",
    bind=True,
    max_retries=0,
    soft_time_limit=120,
    time_limit=150,
)
def retry_failed_nc_tasks(self) -> dict:
    """将 FAILED 且未超出最大重试次数的任务重置为 PENDING，由下一轮 process 再次执行。

    Returns:
        dict: 执行摘要，包含 reset_count 计数。
    """
    qs = NcSyncTask.objects.filter(
        status=SyncStatus.FAILED,
        retry_count__lt=NcSyncTask.MAX_RETRIES,
    )
    count = qs.update(status=SyncStatus.PENDING)
    logger.info("[nc_sync_tasks][retry_failed] reset_count=%s", count)
    return {"reset_count": count}
