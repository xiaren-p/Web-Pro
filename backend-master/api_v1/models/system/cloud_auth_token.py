"""云认证令牌模型。"""
from django.contrib.auth.models import User
from django.db import models

from api_v1.models._base import TimeStampedModel


class CloudAuthToken(TimeStampedModel):
    """缓存 Seafile cloud token（临时）。

    说明：用于在用户登录后，后端使用该用户凭据向 Seafile 获取 token 并缓存，
    仅用于后端对 Seafile 的短期代理请求。前端**不**直接使用此 token。
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cloud_token",
        verbose_name="所属用户",
    )

    site = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="云站点地址",
    )

    token = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="云 Token",
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="到期时间",
    )

    class Meta:
        verbose_name = "云认证令牌"
        verbose_name_plural = "云认证令牌"
