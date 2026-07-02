"""字典类型模型。"""
from django.db import models

from apps.system.models._base import TimeStampedModel


class DictType(TimeStampedModel):
    """字典类型表。"""

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="字典编码",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="字典名称",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    class Meta:
        ordering = ["code"]
        db_table = 'api_v1_dicttype'
        verbose_name = "字典类型"
        verbose_name_plural = "字典类型"

    def __str__(self) -> str:
        """返回模型的字符串表示。"""
        return self.name

