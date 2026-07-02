"""通知推送目标用户模型。"""
from django.contrib.auth.models import User
from django.db import models

from apps.system.models._base import TimeStampedModel
from apps.notice.models.notice import Notice


class NoticeTarget(TimeStampedModel):
    """通知指定目标用户。"""

    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name="targets",
        verbose_name="关联公告",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notice_targets",
        verbose_name="接收用户",
    )

    class Meta:
        db_table = "api_v1_noticetarget"
        verbose_name = "通知目标"
        verbose_name_plural = "通知目标"
        unique_together = (("notice", "user"),)

