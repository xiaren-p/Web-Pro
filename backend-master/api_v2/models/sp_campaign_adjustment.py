"""广告活动调整记录表（sp_campaign_adjustment）。

记录广告活动维度的预算调整、手动预算调整、广告活动暂停、广告活动启用操作。
"""
from django.db import models

from api_v2.models.sp_bid_adjustment import AdjustmentStatusChoices, ExecutionStatusChoices


class CampaignExecutionTypeChoices(models.TextChoices):
    """广告活动调整执行类型枚举。"""

    RULE_BUDGET_ADJUSTMENT = "RULE_BUDGET_ADJUSTMENT", "规则预算调整"
    MANUAL_BUDGET_ADJUSTMENT = "MANUAL_BUDGET_ADJUSTMENT", "手动预算调整"
    CAMPAIGN_PAUSE = "CAMPAIGN_PAUSE", "广告活动暂停"
    CAMPAIGN_ENABLE = "CAMPAIGN_ENABLE", "广告活动启用"


class SpCampaignAdjustment(models.Model):
    """广告活动调整记录表。"""

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 ID",
    )

    execution_type = models.CharField(
        max_length=50,
        choices=CampaignExecutionTypeChoices.choices,
        verbose_name="执行类型",
    )

    auto_rule_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="触发规则 ID",
        help_text="规则命中时写入关联的规则 ID",
    )

    budget_before = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="预算调整前",
    )

    budget_after = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="预算调整后",
    )

    adjustment_status = models.CharField(
        max_length=20,
        choices=AdjustmentStatusChoices.choices,
        default=AdjustmentStatusChoices.PENDING,
        verbose_name="调整状态",
    )

    adjustment_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="调整时间",
    )

    execution_status = models.CharField(
        max_length=20,
        choices=ExecutionStatusChoices.choices,
        default=ExecutionStatusChoices.PENDING,
        verbose_name="执行状态",
    )

    msg = models.TextField(
        default="",
        blank=True,
        verbose_name="执行日志回写",
    )

    operator = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="操作人",
        help_text="用户手动操作时写入用户昵称；任务自动写入时留空",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        db_table = "sp_campaign_adjustment"
        verbose_name = "广告活动调整记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign_id", "profile_id"]),
            models.Index(fields=["execution_type"]),
            models.Index(fields=["execution_status"]),
            models.Index(fields=["adjustment_time"]),
        ]

    def __str__(self) -> str:
        return f"SpCampaignAdjustment<campaign={self.campaign_id}, {self.execution_type}>"
