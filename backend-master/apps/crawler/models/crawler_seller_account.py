"""卖家精灵账号配置模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class CrawlerSellerAccount(TimeStampedModel):
    """卖家精灵账号配置（供爬虫 / 任务使用）。

    注意：密码以明文保存用于对外系统认证，后续迭代可考虑加密。
    """

    username = models.CharField(
        max_length=200,
        verbose_name="账号",
    )

    password = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="密码",
    )

    status = models.IntegerField(
        default=1,
        verbose_name="状态",
    )

    order_num = models.IntegerField(
        default=0,
        verbose_name="排序号",
    )

    class Meta:
        verbose_name = "卖家精灵账号"
        verbose_name_plural = "卖家精灵账号"
        ordering = ("order_num", "id")

