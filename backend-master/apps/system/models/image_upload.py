"""图片上传记录模型。"""
from django.db import models

from apps.system.models._base import TimeStampedModel


class ImageUploadStatus(models.TextChoices):
    """图片上传状态枚举。"""

    NORMAL = "normal", "正常"
    WARNING = "warning", "警告"
    ERROR = "error", "错误"


class ImageUpload(TimeStampedModel):
    """图片上传记录。"""

    image_group = models.CharField(
        max_length=255,
        verbose_name="图片组",
    )

    cloud_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Cloud 路径",
        help_text="允许为空以便前端省略",
    )

    status = models.CharField(
        max_length=50,
        choices=ImageUploadStatus.choices,
        blank=True,
        null=True,
        verbose_name="状态",
    )

    log = models.TextField(
        blank=True,
        null=True,
        verbose_name="日志",
    )

    image_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="图片 URL",
    )

    failed_shops = models.TextField(
        blank=True,
        null=True,
        default=None,
        verbose_name="同步失败的店铺ID列表",
        help_text="None=从未同步；空串=全部成功；逗号分隔 sid=部分失败待重试",
    )

    class Meta:
        db_table = "sys_image_upload"
        verbose_name = "图片上传记录"
        verbose_name_plural = "图片上传记录"
        ordering = ("-created_at",)

