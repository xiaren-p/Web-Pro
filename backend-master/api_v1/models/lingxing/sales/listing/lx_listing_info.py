"""Listing 基础信息模型（lx_listing_info，managed=False）。"""
from django.db import models


class LxListingInfo(models.Model):
    """Listing 基础表。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="Listing 产品ID",
    )

    msku = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="MSKU",
    )

    fnsku = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="FNSKU",
    )

    status = models.IntegerField(
        default=0,
        verbose_name="状态",
    )

    product_link = models.ForeignKey(
        "LxProductInfo",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_column="asin",
        to_field="asin",
        related_name="listings",
        verbose_name="关联产品",
    )

    item_name = models.TextField(
        blank=True,
        null=True,
        verbose_name="标题",
    )

    shop_link = models.ForeignKey(
        "LxSellers",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_column="store_id",
        to_field="id",
        related_name="listings",
        verbose_name="关联店铺",
    )

    fulfillment_channel_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="配送方式",
    )

    amz_product_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="商品编码",
    )

    amz_product_id_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="商品编码类型",
    )

    parent_asin = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="父体ASIN",
    )

    variant_text = models.JSONField(
        blank=True,
        null=True,
        verbose_name="变体属性",
    )

    seller_category = models.TextField(
        blank=True,
        null=True,
        verbose_name="大类类目",
    )

    seller_rank = models.IntegerField(
        default=0,
        verbose_name="大类排名",
    )

    small_rank = models.IntegerField(
        default=0,
        verbose_name="小类排名",
    )

    small_category = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="小类类目",
    )

    stars = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="评分",
    )

    reviews_num = models.IntegerField(
        default=0,
        verbose_name="Rating总数",
    )

    pair_type = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="配对方式",
    )

    open_date_time = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="创建时间",
    )

    on_sale_time = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="开售时间",
    )

    first_order_time = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="首单时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_listing_info"
        verbose_name = "Listing 基础表"
        verbose_name_plural = "Listing 基础表"

