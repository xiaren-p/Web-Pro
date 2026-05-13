"""Listing 业务指标模型（lx_listing_metrics，managed=False）。"""
from django.db import models

from api_v1.models.listing.lx_listing_info import LxListingInfo


class LxListingMetrics(models.Model):
    """Listing 业务指标表。"""

    listing = models.OneToOneField(
        LxListingInfo,
        on_delete=models.DO_NOTHING,
        primary_key=True,
        db_column="listing_id",
        related_name="metrics",
        verbose_name="关联 Listing",
    )

    regular_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="售价",
    )

    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="价格",
    )

    landed_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="优惠价",
    )

    b2b_price = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="B2B价格",
    )

    listing_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Listing价格",
    )

    afn_fulfillable_quantity = models.IntegerField(
        default=0,
        verbose_name="FBA可售",
    )

    fba_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="预估FBA费",
    )

    referral_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="平台费",
    )

    yesterday_volume = models.IntegerField(
        default=0,
        verbose_name="昨日销量",
    )

    total_volume = models.IntegerField(
        default=0,
        verbose_name="7天销量",
    )

    fourteen_volume = models.IntegerField(
        default=0,
        verbose_name="14天销量",
    )

    thirty_volume = models.IntegerField(
        default=0,
        verbose_name="30天销量",
    )

    average_seven_volume = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="7天日均销量",
    )

    average_fourteen_volume = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="14天日均销量",
    )

    average_thirty_volume = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="30天日均销量",
    )

    yesterday_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="昨日销售额",
    )

    seven_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="7天销售额",
    )

    fourteen_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="14天销售额",
    )

    thirty_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="30天销售额",
    )

    yesterday_spend = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="昨日广告费",
    )

    seven_spend = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="7天广告费",
    )

    fourteen_spend = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="14天广告费",
    )

    thirty_spend = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="30天广告费",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_listing_metrics"
        verbose_name = "Listing业务指标表"
        verbose_name_plural = "Listing业务指标表"

