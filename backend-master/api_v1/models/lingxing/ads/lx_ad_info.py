"""广告投放基础信息模型（lx_ad_info，managed=False）。"""
from django.db import models


class LxAdInfo(models.Model):
    """广告投放（Product Ad）基础信息表。

    每条记录对应亚马逊广告中的一个 Product Ad（广告投放），
    通过 ad_group_id + campaign_id + profile_id 归属到对应广告组/广告活动/店铺。
    ORM 只读取数据，不参与迁移（managed=False）。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    ad_id = models.CharField(
        max_length=100,
        verbose_name="广告投放 ID",
    )

    asin = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="商品 ASIN",
    )

    listing_price = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Listing 售价（原始字符串）",
    )

    product_name = models.TextField(
        null=True,
        blank=True,
        verbose_name="商品标题",
    )

    stars = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name="星级评分（原始字符串）",
    )

    review_count = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="评论数（原始字符串）",
    )

    sku = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="商家 SKU（MSKU）",
    )

    main_img = models.TextField(
        null=True,
        blank=True,
        verbose_name="商品主图 URL",
    )

    state = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="有效状态",
        help_text="enabled / paused / archived",
    )

    service_status = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="服务状态（平台层面）",
    )

    portfolio_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="所属广告组合 ID",
    )

    ad_group_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="所属广告组 ID",
    )

    campaign_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="所属广告活动 ID",
    )

    profile_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="店铺 Profile ID",
    )

    creation_date = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="创建时间（原始字符串）",
    )

    afn_fulfillable_quantity = models.IntegerField(
        default=0,
        verbose_name="FBA 可售库存",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_ad_info"
        verbose_name = "广告投放基础信息表"
        verbose_name_plural = "广告投放基础信息表"
        unique_together = (("ad_id", "campaign_id", "profile_id"),)
        ordering = ["ad_id"]

    def __str__(self) -> str:
        return f"LxAdInfo<{self.ad_id}>"
