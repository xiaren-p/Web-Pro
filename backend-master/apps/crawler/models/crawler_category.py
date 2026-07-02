"""爬取类目模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class CrawlerCategory(TimeStampedModel):
    """爬取类目表。前端字段映射：name / category_id / site / category_type / status。"""

    name = models.CharField(
        max_length=200,
        verbose_name="类目名称",
    )

    category_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="类目 ID",
    )

    site = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="站点",
    )

    category_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="类目类型",
    )

    status = models.IntegerField(
        default=1,
        verbose_name="状态",
    )

    class Meta:
        verbose_name = "爬取类目"
        verbose_name_plural = "爬取类目"
        ordering = ("-created_at", "id")

