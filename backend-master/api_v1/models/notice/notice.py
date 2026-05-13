"""通知公告模型。"""
from django.contrib.auth.models import User
from django.db import models

from api_v1.models._base import TimeStampedModel


class NoticeLevel(models.TextChoices):
    """通知优先级枚举。"""

    LOW = "L", "低"
    MEDIUM = "M", "中"
    HIGH = "H", "高"


class NoticeStatus(models.TextChoices):
    """通知状态枚举。"""

    DRAFT = "draft", "草稿"
    PUBLISHED = "published", "已发布"
    REVOKED = "revoked", "已撤回"


class NoticeTargetType(models.IntegerChoices):
    """通知推送目标类型枚举。"""

    ALL = 1, "全体用户"
    SPECIFIED = 2, "指定用户"


class Notice(TimeStampedModel):
    """通知公告。"""

    title = models.CharField(
        max_length=200,
        verbose_name="标题",
    )

    content = models.TextField(
        blank=True,
        default="",
        verbose_name="内容",
    )

    type = models.CharField(
        max_length=50,
        blank=True,
        default="general",
        verbose_name="通知类型",
    )

    level = models.CharField(
        max_length=20,
        choices=NoticeLevel.choices,
        default=NoticeLevel.LOW,
        verbose_name="优先级",
    )

    target_type = models.IntegerField(
        choices=NoticeTargetType.choices,
        default=NoticeTargetType.ALL,
        verbose_name="推送目标类型",
    )

    status = models.CharField(
        max_length=20,
        choices=NoticeStatus.choices,
        default=NoticeStatus.DRAFT,
        verbose_name="状态",
    )

    publish_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="发布时间",
    )

    revoke_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="撤回时间",
    )

    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="创建人",
    )

    class Meta:
        verbose_name = "通知公告"
        verbose_name_plural = "通知公告"

    def __str__(self) -> str:
        return self.title

