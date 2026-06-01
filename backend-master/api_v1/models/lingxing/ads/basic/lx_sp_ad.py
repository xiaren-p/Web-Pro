"""SP 广告商品基础数据表（lx_sp_ad）。"""
from django.db import models


class LxSpAd(models.Model):
    """SP 广告商品基础数据表（领星 → 广告 → 基础数据 → SP 广告商品）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    ad_group_id = models.BigIntegerField(
        verbose_name="广告组 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 Profile ID",
    )

    ad_id = models.BigIntegerField(
        verbose_name="商品广告 ID",
    )

    state = models.CharField(
        max_length=50,
        default="",
        verbose_name="状态",
    )

    sku = models.CharField(
        max_length=100,
        default="",
        verbose_name="MSKU",
    )

    asin = models.CharField(
        max_length=50,
        default="",
        verbose_name="ASIN",
    )

    serving_status = models.CharField(
        max_length=100,
        default="",
        verbose_name="服务状态",
    )

    creation_date = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="创建时间（毫秒时间戳）",
    )

    last_updated_date = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="最后更新时间（毫秒时间戳）",
    )

    class Meta:
        db_table = "lx_sp_ad"
        verbose_name = "SP 广告商品"
        verbose_name_plural = "SP 广告商品列表"
        ordering = ["-creation_date"]
        unique_together = (("ad_id", "profile_id"),)

    def __str__(self) -> str:
        return f"LxSpAd<{self.ad_id}> {self.sku}"
