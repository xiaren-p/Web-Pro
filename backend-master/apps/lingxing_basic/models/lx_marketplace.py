"""亚马逊市场列表（lx_marketplace）。"""
from django.db import models


class LxMarketplace(models.Model):
    """亚马逊市场列表（领星 → 基础数据 → 站点列表）。"""

    mid = models.IntegerField(
        primary_key=True,
        verbose_name="站点 ID",
    )

    region = models.CharField(
        max_length=20,
        verbose_name="地区",
    )

    aws_region = models.CharField(
        max_length=50,
        verbose_name="亚马逊地区",
    )

    country = models.CharField(
        max_length=50,
        verbose_name="商城所在国家名称",
    )

    code = models.CharField(
        max_length=10,
        verbose_name="亚马逊国家 code",
    )

    marketplace_id = models.CharField(
        max_length=64,
        verbose_name="亚马逊市场 ID",
    )

    class Meta:
        managed = True
        db_table = "lx_marketplace"
        verbose_name = "亚马逊市场列表"
        verbose_name_plural = "亚马逊市场列表"
        ordering = ["mid"]

    def __str__(self) -> str:
        return f"LxMarketplace<{self.mid} {self.code}>"
