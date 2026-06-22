"""图片同步队列业务服务。

将原外部 API（cloud.hanlis.cn:9898）的同步队列存储职责收归内部，
所有 upsert 与查询逻辑集中在此 service，view 层仅做 HTTP 解析与响应包装。
"""
import logging

from django.db.models import QuerySet
from django.utils import timezone

from api_v1.models import ImageSyncQueue
from api_v1.models.file.image_sync_queue import ImageSyncStatus

logger = logging.getLogger(__name__)


def upsert_sync_task(image_upload) -> tuple[bool, str]:
    """根据 ImageUpload 记录 upsert 同步队列。

    存在相同 sku 的队列记录则更新 local_path 并重置状态为 PENDING，
    不存在则创建新记录。同时向 ImageUpload.log 追加操作日志。

    Args:
        image_upload: ImageUpload 模型实例。

    Returns:
        tuple[bool, str]: (是否成功, 日志行文本)。
    """
    sku = image_upload.image_group
    local_path = image_upload.cloud_path or ""

    try:
        ImageSyncQueue.objects.update_or_create(
            sku=sku,
            defaults={
                "local_path": local_path,
                "status": ImageSyncStatus.PENDING,
                "error_msg": "",
            },
        )
    except Exception as exc:
        logger.error(
            "[ImageSyncQueueService][upsert_sync_task] upsert 失败 sku=%s: %s",
            sku,
            exc,
            exc_info=True,
        )
        now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{now_str}] 同步失败: {exc}"
        _append_log(image_upload, log_line)
        return False, log_line

    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{now_str}] 已提交同步队列！"
    _append_log(image_upload, log_line)
    logger.info("[ImageSyncQueueService][upsert_sync_task] 已提交同步队列 sku=%s", sku)
    return True, log_line


def batch_upsert_sync_tasks(image_uploads: list) -> list[dict]:
    """批量 upsert 同步队列。

    Args:
        image_uploads: ImageUpload 实例列表。

    Returns:
        list[dict]: 每条结果，结构 {id, success, msg}。
    """
    results: list[dict] = []
    for instance in image_uploads:
        success, log_line = upsert_sync_task(instance)
        results.append({
            "id": instance.id,
            "success": success,
            "msg": log_line,
        })
    return results


def get_queue_queryset(query_params: dict) -> QuerySet:
    """根据查询参数构建同步队列 queryset。

    Args:
        query_params: 含 imageGroup（可选）等过滤参数的字典。

    Returns:
        QuerySet: 过滤后的 ImageSyncQueue 查询集（按 created_at 倒序）。
    """
    qs = ImageSyncQueue.objects.all()
    image_group = query_params.get("imageGroup")
    if image_group:
        qs = qs.filter(sku__icontains=image_group)
    return qs


def _append_log(image_upload, log_line: str) -> None:
    """向 ImageUpload 记录追加日志行。

    Args:
        image_upload: ImageUpload 模型实例。
        log_line: 待追加的日志文本。
    """
    current_log = image_upload.log or ""
    image_upload.log = f"{current_log}\n{log_line}".strip()
    image_upload.save(update_fields=["log"])
