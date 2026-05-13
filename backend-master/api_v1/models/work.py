"""工作汇报数据模型。"""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from api_v1.models._base import TimeStampedModel


class ReportType(models.TextChoices):
    """工作汇报类型枚举。"""

    DAILY = "daily", "日报"
    WEEKLY = "weekly", "周报"


class WorkReport(TimeStampedModel):
    """工作汇报（日报 / 周报）。"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="work_reports",
        verbose_name="用户",
    )

    type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        default=ReportType.DAILY,
        verbose_name="汇报类型",
    )

    content = models.TextField(
        blank=True,
        default="",
        verbose_name="今日工作内容",
    )

    plan = models.TextField(
        blank=True,
        default="",
        verbose_name="明日工作计划",
    )

    issues = models.TextField(
        blank=True,
        default="",
        verbose_name="遇到的问题 / 需要协助",
    )

    work_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=8.0,
        verbose_name="工时（小时）",
    )

    progress = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="完成进度（%）",
    )

    report_date = models.DateField(
        default=timezone.now,
        verbose_name="汇报日期",
    )

    class Meta:
        verbose_name = "工作汇报"
        verbose_name_plural = "工作汇报"
        ordering = ("-report_date", "-created_at")

    def __str__(self) -> str:
        return f"{self.user.username} {self.report_date} {self.type}"

