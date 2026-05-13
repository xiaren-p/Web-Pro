"""字典类型模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


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
        verbose_name = "字典类型"
        verbose_name_plural = "字典类型"

    def __str__(self) -> str:
        return self.name

