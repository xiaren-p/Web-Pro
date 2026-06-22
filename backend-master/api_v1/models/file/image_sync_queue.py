"""图片同步队列表（sys_image_sync_queue）。

替代原外部 API cloud.hanlis.cn:9898 的队列存储职责，
内部管理待同步的图片组（SKU）及其路径与同步状态。
"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class ImageSyncStatus(models.TextChoices):
    """图片同步状态枚举。"""

    PENDING = "pending", "待同步"
    SUCCESS = "success", "同步成功"
    FAILED = "failed", "同步失败"


class ImageSyncQueue(TimeStampedModel):
    """图片同步队列记录。

    记录需要同步的图片组（SKU）及其本地路径，由 sync / batch_sync
    操作写入，queue 接口查询展示。
    """

    sku = models.CharField(
        max_length=255,
        verbose_name="图片组 SKU",
    )

    local_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="本地路径",
    )

    status = models.CharField(
        max_length=20,
        choices=ImageSyncStatus.choices,
        default=ImageSyncStatus.PENDING,
        verbose_name="同步状态",
    )

    error_msg = models.TextField(
        blank=True,
        default="",
        verbose_name="错误信息",
    )

    class Meta:
        db_table = "sys_image_sync_queue"
        verbose_name = "图片同步队列"
        verbose_name_plural = "图片同步队列"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"ImageSyncQueue<{self.sku}>"
