"""月度前 20 天亏损订单统计模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class MonthlyLossOrderFirst20(TimeStampedModel):
    """月度前 20 天亏损订单统计。与 MonthlyLossOrder 字段一致。"""

    image_url = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="图片URL",
    )

    msku = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="MSKU",
    )

    asin = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="ASIN",
    )

    parent_asin = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="父ASIN",
    )

    store_country = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="店铺/国家",
    )

    product_name_sku = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="品名/SKU",
    )

    gross_profit = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="毛利润",
    )

    gross_margin = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="毛利率",
    )

    net_gross_margin = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="净毛利率",
    )

    return_rate = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="退货率",
    )

    refund_amount_rate = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="退款率",
    )

    total_stock_fee = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="仓储费",
    )

    spend = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="广告费",
    )

    spend_rate = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="广告率费",
    )

    sales = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name="销量",
    )

    owner = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="负责人",
    )

    month = models.CharField(
        max_length=7,
        db_index=True,
        verbose_name="月份",
        help_text="YYYY-MM",
    )

    class Meta:
        verbose_name = "月度前20天亏损订单统计"
        verbose_name_plural = "月度前20天亏损订单统计"
        ordering = ("-month", "-id")

    def __str__(self) -> str:
        return f"{self.msku} {self.asin} {self.month}"

