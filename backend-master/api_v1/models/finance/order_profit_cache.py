"""OrderProfit 缓存模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class OrderProfitCache(TimeStampedModel):
    """缓存从 LingXing /basicOpen/finance/mreport/OrderProfit 拉取的原始数据。

    `created_at` 来自 TimeStampedModel，可用于判断是否超过缓存有效期。
    """

    key = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        verbose_name="缓存唯一键",
        help_text="基于请求参数的唯一 key（例如 sids,startDate,endDate,currency,searchValue 哈希）",
    )

    params = models.TextField(
        blank=True,
        default="",
        verbose_name="原始参数 JSON",
    )

    data = models.TextField(
        blank=True,
        default="",
        verbose_name="响应 data 序列化字符串",
    )

    class Meta:
        verbose_name = "OrderProfit 缓存"
        verbose_name_plural = "OrderProfit 缓存"
        indexes = [
            models.Index(fields=["created_at"]),
        ]

