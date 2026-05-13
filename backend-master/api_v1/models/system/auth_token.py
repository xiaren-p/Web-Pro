"""认证令牌模型。"""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from api_v1.models._base import TimeStampedModel


class AuthToken(TimeStampedModel):
    """简单的访问 / 刷新令牌。"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tokens",
        verbose_name="所属用户",
    )

    access_token = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="访问令牌",
    )

    refresh_token = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="刷新令牌",
    )

    access_expires_at = models.DateTimeField(
        verbose_name="访问令牌到期时间",
    )

    refresh_expires_at = models.DateTimeField(
        verbose_name="刷新令牌到期时间",
    )

    revoked = models.BooleanField(
        default=False,
        verbose_name="是否已吊销",
    )

    class Meta:
        verbose_name = "认证令牌"
        verbose_name_plural = "认证令牌"
        indexes = [
            models.Index(fields=["access_token"]),
            models.Index(fields=["refresh_token"]),
        ]

    def is_access_valid(self) -> bool:
        """访问令牌是否仍在有效期且未被吊销。"""
        return (not self.revoked) and timezone.now() < self.access_expires_at

    def is_refresh_valid(self) -> bool:
        """刷新令牌是否仍在有效期且未被吊销。"""
        return (not self.revoked) and timezone.now() < self.refresh_expires_at

