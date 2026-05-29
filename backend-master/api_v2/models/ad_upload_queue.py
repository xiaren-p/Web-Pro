"""广告活动上传队列记录表（api_v2_ad_upload_queue）。

由 xlsx 文件解析后，按（广告活动 × 国家）粒度拆分落库，每条记录对应一个站点的独立队列项。
"""

from django.contrib.auth.models import User
from django.db import models


class AdParseStatus(models.IntegerChoices):
    """广告队列解析状态枚举。"""

    FAILED = 0, "解析失败"
    SUCCESS = 1, "解析成功"


class CampaignSubmitStatus(models.IntegerChoices):
    """广告活动 API 提交状态枚举。"""

    PENDING = 0, "待提交"
    SUCCESS = 1, "提交成功"
    FAILED = 2, "提交失败"


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

    skus = models.JSONField(
        default=list,
        verbose_name="SKU 列表",
    )

    keywords = models.JSONField(
        default=list,
        verbose_name="关键词列表",
    )

    parse_status = models.IntegerField(
        choices=AdParseStatus.choices,
        default=AdParseStatus.SUCCESS,
        db_index=True,
        verbose_name="解析状态",
    )

    campaign_status = models.IntegerField(
        choices=CampaignSubmitStatus.choices,
        default=CampaignSubmitStatus.PENDING,
        db_index=True,
        verbose_name="API 提交状态",
    )

    campaign_response = models.JSONField(
        default=dict,
        verbose_name="API 响应数据",
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
