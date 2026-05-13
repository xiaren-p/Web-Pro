"""文件夹模型。"""
from django.contrib.auth.models import User
from django.db import models

from api_v1.models._base import TimeStampedModel


class FileFolder(TimeStampedModel):
    """文件夹。

    使用 external_id 与前端传入的 fileId / hash 保持对应，避免与内部主键耦合。
    根目录以 parent=None 表示；逻辑删除采用 is_deleted + deleted_at。
    """

    external_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="外部 ID",
        help_text="前端生成的文件夹 ID",
    )

    name = models.CharField(
        max_length=255,
        verbose_name="文件夹名",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父文件夹",
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="拥有者",
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
        verbose_name = "文件夹"
        verbose_name_plural = "文件夹"
        indexes = [
            models.Index(fields=["external_id"]),
            models.Index(fields=["is_deleted"]),
        ]

    def __str__(self) -> str:
        return self.name

