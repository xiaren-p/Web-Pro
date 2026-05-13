"""系统参数配置模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class Config(TimeStampedModel):
    """系统参数配置。"""

    key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="参数键",
    )

    value = models.TextField(
        blank=True,
        default="",
        verbose_name="参数值",
    )

    remark = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    class Meta:
        verbose_name = "系统参数"
        verbose_name_plural = "系统参数"

    def __str__(self) -> str:
        return self.key

