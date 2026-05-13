"""广告组合模型（lx_ad_portfolios，managed=False）。"""
from django.db import models


class LxAdPortfolios(models.Model):
    """广告组合表。"""

    portfolio_id = models.BigIntegerField(
        primary_key=True,
        verbose_name="主键",
    )

    profile_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="店铺 Profile ID",
    )

    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="名称",
    )

    budget = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="预算",
    )

    in_budget = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name="预算内外",
    )

    state = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="状态",
    )

    budget_controls = models.TextField(
        null=True,
        blank=True,
        verbose_name="预算控制",
    )

    store_country = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="国家代码",
    )

    store_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="店铺名称",
    )

    store_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="店铺类型",
    )

    store_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="店铺 ID",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_ad_portfolios"
        verbose_name = "广告组合表"
        verbose_name_plural = "广告组合表"

