"""爬虫日志模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class CrawlerLogLevel(models.TextChoices):
    """爬虫日志级别枚举。"""

    DEBUG = "debug", "Debug"
    INFO = "info", "Info"
    WARN = "warn", "Warn"
    ERROR = "error", "Error"


class CrawlerLog(TimeStampedModel):
    """爬虫专用日志表（与系统操作日志分离）。"""

    module = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="日志来源模块",
    )

    content = models.TextField(
        blank=True,
        default="",
        verbose_name="日志内容",
    )

    level = models.CharField(
        max_length=10,
        choices=CrawlerLogLevel.choices,
        default=CrawlerLogLevel.INFO,
        verbose_name="日志级别",
    )

    elapsed_ms = models.IntegerField(
        default=0,
        verbose_name="模块耗时（毫秒）",
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

    class Meta:
        verbose_name = "爬虫日志"
        verbose_name_plural = "爬虫日志"
        ordering = ("-id",)

