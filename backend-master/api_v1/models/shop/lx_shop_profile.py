"""店铺 Profile 镜像模型（lx_shop_profiles，managed=False）。"""
from django.db import models


class LxShopProfile(models.Model):
    """店铺 Profile 数据表。"""

    profile_id = models.CharField(
        max_length=100,
        primary_key=True,
        verbose_name="主键",
    )

    alias = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="别名",
    )

    country = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name="国家代码",
    )

    type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="类型",
    )

    created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="创建时间",
    )

    local_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="当地时间",
    )

    report_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="报告时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_shop_profiles"
        verbose_name = "店铺 Profiles"
        verbose_name_plural = "店铺 Profiles"

