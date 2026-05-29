"""Listing 图片上传 / 更新 Celery 任务（listing_image_upload_task，运行于单线程队列）。"""

import logging

from celery import shared_task
from django.utils import timezone

from api_v2.models.workflow_execution import ExecutionStatus, WorkflowExecution

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='api_v2.tasks.listing_image_upload_task.upload_listing_images_task',
    max_retries=0,
    soft_time_limit=1500,
    time_limit=1800,
)
def upload_listing_images_task(self, execution_id: int, listing_id: int, image_ids: list[int], **kwargs) -> dict:
    """
    Listing 图片上传 / 更新任务。

    运行于 single_thread_queue（concurrency=1），保证同一时刻只有一个图片上传任务在执行，
    避免与外部图片服务产生并发写冲突。
    任务开始时将执行记录状态更新为 running，完成后更新为 completed 或 failed。

    Args:
        execution_id (int): 工作流执行记录 ID（WorkflowExecution.pk）。
        listing_id (int): 目标 Listing 的 ID。
        image_ids (list[int]): 需要上传或更新的图片 ID 列表（来自本地图片表）。
        **kwargs: 保留扩展参数，不参与当前逻辑。

    Returns:
        dict: 上传结果摘要，包含 listing_id、uploaded_count、failed_ids 字段。

    Raises:
        Exception: 任务失败时抛出原始异常，执行状态自动更新为 failed。
    """
    execution: WorkflowExecution | None = None

    try:
        execution = WorkflowExecution.objects.get(id=execution_id)
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = timezone.now()
        execution.save(update_fields=['status', 'started_at'])

        logger.info(
            "[upload_listing_images_task] 开始执行: execution_id=%s listing_id=%s image_count=%s",
            execution_id,
            listing_id,
            len(image_ids),
        )

        # TODO(实现): 调用 Listing 图片上传 Service
        # from api_v2.services.listing_image_upload_service import ListingImageUploadService
        # result = ListingImageUploadService().upload(listing_id, image_ids)
        result: dict = {
            'listing_id': listing_id,
            'uploaded_count': 0,
            'failed_ids': [],
        }

        execution.status = ExecutionStatus.COMPLETED
        execution.result = result
        execution.completed_at = timezone.now()
        execution.save(update_fields=['status', 'result', 'completed_at'])

        logger.info(
            "[upload_listing_images_task] 执行完成: execution_id=%s uploaded=%s",
            execution_id,
            result['uploaded_count'],
        )

        return result

    except Exception as exc:
        if execution is not None:
            execution.status = ExecutionStatus.FAILED
            execution.error_msg = str(exc)
            execution.completed_at = timezone.now()
            execution.save(update_fields=['status', 'error_msg', 'completed_at'])

        logger.error(
            "[upload_listing_images_task] 执行失败: execution_id=%s exc=%s",
            execution_id,
            exc,
            exc_info=True,
        )
        raise
