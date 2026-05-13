"""文件分片记录模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel
from api_v1.models.file.file_asset import FileAsset


class FileChunk(TimeStampedModel):
    """文件分片记录，用于断点续传去重。"""

    asset = models.ForeignKey(
        FileAsset,
        on_delete=models.CASCADE,
        related_name="chunks",
        verbose_name="所属文件",
    )

    chunk_hash = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="分片哈希",
    )

    num = models.IntegerField(
        verbose_name="分片序号",
        help_text="从 0 开始",
    )

    size = models.BigIntegerField(
        default=0,
        verbose_name="分片大小（字节）",
    )

    storage_path = models.CharField(
        max_length=255,
        verbose_name="存储相对路径",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="上传时间",
    )

    class Meta:
        verbose_name = "文件分片"
        verbose_name_plural = "文件分片"
        unique_together = ("asset", "num")
        indexes = [
            models.Index(fields=["chunk_hash"]),
        ]

    def __str__(self) -> str:
        return f"{self.asset_id}:{self.num}"

