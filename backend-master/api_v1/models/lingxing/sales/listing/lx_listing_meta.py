"""Listing 通用元数据表（lx_listing_meta）。

以 OneToOneField 关联 LxListingData，承载备注(remark_text)与分类(assort)。
后续可横向扩展字段，避免频繁改动主表。
"""
from django.db import models

from api_v1.models.lingxing.sales.listing.lx_listing_data import LxListingData


class LxListingMeta(models.Model):
    """Listing 通用元数据表。

    每个 LxListingData 最多对应一条记录，字段独立维护。
    """

    listing_data = models.OneToOneField(
        LxListingData,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="listing_data_id",
        related_name="meta",
        verbose_name="关联 Listing 数据",
    )

    remark_text = models.TextField(
        blank=True,
        null=True,
        verbose_name="备注",
    )

    assort = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="分类",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        db_table = "lx_listing_meta"
        verbose_name = "Listing 通用元数据"
        verbose_name_plural = "Listing 通用元数据列表"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"LxListingMeta<listing_data={self.listing_data_id}>"
