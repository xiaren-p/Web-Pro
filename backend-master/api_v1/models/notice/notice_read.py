"""公告已读记录模型。"""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from api_v1.models._base import TimeStampedModel
from api_v1.models.notice.notice import Notice


class NoticeRead(TimeStampedModel):
    """用户 - 公告已读记录。

    用于记录某用户已读的公告，前端展示“我的公告 / 未读”时可以排除已读项。
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notice_reads",
        verbose_name="用户",
    )

    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name="reads",
        verbose_name="关联公告",
    )

    read_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="读取时间",
    )

    class Meta:
        verbose_name = "公告已读"
        verbose_name_plural = "公告已读"
        unique_together = (("user", "notice"),)

