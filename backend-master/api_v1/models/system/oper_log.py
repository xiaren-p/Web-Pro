"""操作日志模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class OperLog(TimeStampedModel):
    """操作日志。"""

    module = models.CharField(
        max_length=100,
        verbose_name="模块名称",
    )

    action = models.TextField(
        verbose_name="操作描述",
    )

    operator = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="操作人",
    )

    ip = models.CharField(
        max_length=45,
        blank=True,
        default="",
        verbose_name="请求 IP",
    )

    user_agent = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="User-Agent",
    )

    result = models.CharField(
        max_length=20,
        default="success",
        verbose_name="执行结果",
    )

    elapsed_ms = models.IntegerField(
        default=0,
        verbose_name="耗时（毫秒）",
    )

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ("-id",)

