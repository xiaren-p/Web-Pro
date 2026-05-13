"""Listing 备注模型（lx_listing_remark）。"""
from django.db import models

from api_v1.models.listing.lx_listing_info import LxListingInfo


class LxListingRemark(models.Model):
    """Listing 备注表。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="主键",
    )

    listing = models.OneToOneField(
        LxListingInfo,
        on_delete=models.CASCADE,
        db_column="listing_id",
        related_name="remark",
        db_constraint=False,
        verbose_name="关联 Listing",
    )

    remark_text = models.TextField(
        blank=True,
        null=True,
        verbose_name="备注",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        db_table = "lx_listing_remark"
        verbose_name = "Listing备注"
        verbose_name_plural = "Listing备注"

