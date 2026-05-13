"""店铺（亮礿 Seller）镜像模型（lx_sellers，managed=False）。"""
from django.db import models


class LxSellers(models.Model):
    """店铺信息表。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="主键 ID",
    )

    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="店铺名称",
    )

    seller_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Seller ID",
    )

    country_code = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name="国家代码",
    )

    country = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="国家",
    )

    is_concept = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="是否概念店铺",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_sellers"
        verbose_name = "店铺"
        verbose_name_plural = "店铺"

