"""文件资产模型。"""
from django.contrib.auth.models import User
from django.db import models

from api_v1.models._base import TimeStampedModel
from api_v1.models.file.file_folder import FileFolder


class FileAsset(TimeStampedModel):
    """合并后的文件（逻辑文件）。

    包含上传进度、存储路径、合并状态、逻辑删除标记。
    """

    file_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="文件 ID",
        help_text="前端生成的文件 ID，与数据库主键区分",
    )

    merge_file_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="合并文件 ID",
        help_text="分片阶段生成的临时合并 ID（pid），便于前端关联分片与目标文件",
    )

    name = models.CharField(
        max_length=255,
        verbose_name="文件名",
    )

    size = models.BigIntegerField(
        default=0,
        verbose_name="文件大小（字节）",
    )

    file_hash = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="文件整体哈希",
        help_text="用于秒传 / 断点续传判断",
    )

    ext = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="扩展名",
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="MIME 类型",
    )

    folder = models.ForeignKey(
        FileFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
        verbose_name="所属文件夹",
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="拥有者",
    )

    total_chunks = models.IntegerField(
        default=0,
        verbose_name="分片总数",
    )

    uploaded_chunks = models.IntegerField(
        default=0,
        verbose_name="已上传分片数",
    )

    is_completed = models.BooleanField(
        default=False,
        verbose_name="是否合并完成",
    )

    storage_path = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="存储路径",
    )

    is_deleted = models.BooleanField(
        default=False,
        verbose_name="是否逻辑删除",
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="删除时间",
    )

    class Meta:
        verbose_name = "文件"
        verbose_name_plural = "文件"
        indexes = [
            models.Index(fields=["file_hash"]),
            models.Index(fields=["is_deleted", "is_completed"]),
        ]

    def __str__(self) -> str:
        return self.name

