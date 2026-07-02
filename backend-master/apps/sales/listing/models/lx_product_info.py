"""产品基础信息模型（lx_product_info，managed=False）。"""
from django.db import models


class LxProductInfo(models.Model):
    """产品基础表。"""

    asin = models.CharField(
        max_length=100,
        primary_key=True,
        verbose_name="ASIN",
    )

    product_id = models.BigIntegerField(
        default=0,
        verbose_name="产品ID",
    )

    local_sku = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="本地SKU",
    )

    local_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="品名",
    )

    image = models.TextField(
        blank=True,
        null=True,
        verbose_name="图片",
    )

    brand = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="亚马逊品牌",
    )

    local_brand = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="本地品牌",
    )

    principal_list = models.JSONField(
        blank=True,
        null=True,
        verbose_name="负责人信息",
    )

    assort = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="分类",
    )

    label = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="标签",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_product_info"
        verbose_name = "产品基础表"
        verbose_name_plural = "产品基础表"

