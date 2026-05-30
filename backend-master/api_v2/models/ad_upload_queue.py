"""广告活动上传队列记录表（api_v2_ad_upload_queue）。

由 xlsx 文件解析后，按（广告活动 × 国家）粒度拆分落库，每条记录对应一个站点的独立队列项。

params 字段结构：
    {
        "skus": ["SKU-001", ...],
        "keywords": ["keyword1", ...],
        "daily_budget": 1.00,
        "default_bid": 0.12,
        "close_match_bid": 0.12,
        "loose_match_bid": 0.10,
        "substitutes_bid": 0.10,
        "complements_bid": 0.10
    }

step_ids 字段结构（各步骤提交成功后逐步填入）：
    {
        "campaign_id": "",
        "ad_group_id": "",
        "product_ad_ids": [],
        "keyword_ids": []
    }
"""

from django.contrib.auth.models import User
from django.db import models


class AdParseStatus(models.IntegerChoices):
    """广告队列状态枚举（贯穿解析与提交两个阶段）。"""

    FAILED = 0, "失败"
    PENDING = 1, "队列中"
    SUCCESS = 2, "成功"
    ANOMALY = 3, "异常"


def _default_params() -> dict:
    """广告参数字段默认值工厂。"""
    return {
        "skus": [],
        "keywords": [],
        "daily_budget": 1.00,
        "default_bid": 0.12,
        "close_match_bid": 0.12,
        "loose_match_bid": 0.10,
        "substitutes_bid": 0.10,
        "complements_bid": 0.10,
    }


def _default_step_ids() -> dict:
    """步骤产出 ID 字段默认值工厂。"""
    return {
        "campaign_id": "",
        "ad_group_id": "",
        "product_ad_ids": [],
        "keyword_ids": [],
    }


class AdUploadQueue(models.Model):
    """广告活动上传队列记录。

    由 xlsx 上传接口解析生成，一条记录 = 一个广告活动 × 一个国家站点的组合。
    """

    campaign_name = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="广告活动名称",
    )

    shop = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="店铺名称",
    )

    country = models.CharField(
        max_length=10,
        verbose_name="国家/站点",
    )

    ad_type = models.CharField(
        max_length=20,
        default="sp",
        verbose_name="广告类型",
    )

    params = models.JSONField(
        default=_default_params,
        verbose_name="广告参数",
    )

    step_ids = models.JSONField(
        default=_default_step_ids,
        verbose_name="步骤产出 ID",
    )

    parse_status = models.IntegerField(
        choices=AdParseStatus.choices,
        default=AdParseStatus.PENDING,
        db_index=True,
        verbose_name="状态",
    )

    msg = models.TextField(
        default="成功",
        verbose_name="状态消息",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ad_upload_queues",
        verbose_name="创建用户",
    )

    class Meta:
        db_table = "api_v2_ad_upload_queue"
        verbose_name = "广告上传队列"
        verbose_name_plural = "广告上传队列"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shop", "country"], name="adqueue_shop_country_idx"),
        ]

    def __str__(self) -> str:
        return f"AdUploadQueue<{self.campaign_name}-{self.country}>"
