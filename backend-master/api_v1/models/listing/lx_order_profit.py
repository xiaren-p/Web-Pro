"""产品利润报表模型（lx_order_profit，managed=False）。"""
from django.db import models


class LxOrderProfit(models.Model):
    """产品利润报表。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="主键",
    )

    listing_id = models.BigIntegerField(
        default=0,
        verbose_name="Listing 产品ID",
    )

    report_date = models.DateField(
        verbose_name="报表时间",
    )

    asin = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="ASIN",
    )

    gross_profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="毛利润",
    )

    gross_margin = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0.0000,
        verbose_name="毛利率",
    )

    net_gross_margin = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0.0000,
        verbose_name="净毛利率",
    )

    volume = models.IntegerField(
        default=0,
        verbose_name="销量",
    )

    return_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0.0000,
        verbose_name="退货率",
    )

    refund_amount_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0.0000,
        verbose_name="退款率",
    )

    total_stock_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="仓储费",
    )

    spend = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="广告费",
    )

    spend_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0.0000,
        verbose_name="广告费率",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_order_profit"
        verbose_name = "产品利润报表"
        verbose_name_plural = "产品利润报表"

