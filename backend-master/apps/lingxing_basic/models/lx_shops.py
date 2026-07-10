"""店铺基础数据表（lx_shops，managed=False）。"""
from django.db import models


class ShopStatus(models.IntegerChoices):
    """店铺启用状态枚举。"""

    DISABLED = 0, "禁用"
    ENABLED = 1, "启用"


class HasAdsSetting(models.IntegerChoices):
    """是否配置广告设置枚举。"""

    NO = 0, "未配置"
    YES = 1, "已配置"


class LxShops(models.Model):
    """店铺基础数据表（领星 → 基础数据 → 店铺表）。"""

    sid = models.IntegerField(
        primary_key=True,
        verbose_name="店铺 ID",
    )

    mid = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Marketplace 序号",
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

    account_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="账号名称",
    )

    seller_account_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="卖家账号 ID",
    )

    region = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="大区（如 EU / NA）",
    )

    country = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="国家",
    )

    has_ads_setting = models.IntegerField(
        choices=HasAdsSetting.choices,
        default=HasAdsSetting.NO,
        verbose_name="是否配置广告设置",
    )

    marketplace_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="Marketplace ID",
    )

    status = models.IntegerField(
        choices=ShopStatus.choices,
        default=ShopStatus.ENABLED,
        verbose_name="店铺状态",
    )

    class Meta:
        managed = False
        db_table = "lx_shops"
        verbose_name = "店铺基础数据"
        verbose_name_plural = "店铺基础数据"
        ordering = ["sid"]

    def __str__(self) -> str:
        return f"LxShops<{self.sid} {self.name}>"
