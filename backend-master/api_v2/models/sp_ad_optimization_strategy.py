"""SP 广告优化策略表（sp_ad_optimization_strategy）。

以 (campaign_id, profile_id, targeting_type) 为粒度，
记录 SP 广告活动的自动与手动优化策略规则及当日更新状态。
"""
from django.db import models

from api_v1.models.lingxing.ads.basic.lx_sp_campaign import SpCampaignTargetingType


class ManualRulesStatus(models.IntegerChoices):
    """是否手动设置规则枚举。"""

    YES = 1, "是"
    NO = 0, "否"


class SpAdOptimizationStrategy(models.Model):
    """SP 广告优化策略表。"""

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 Profile ID",
    )

    targeting_type = models.CharField(
        max_length=20,
        choices=SpCampaignTargetingType.choices,
        default=SpCampaignTargetingType.AUTO,
        verbose_name="投放类型",
    )

    auto_rules = models.JSONField(
        default=list,
        verbose_name="自动规则表",
        help_text="系统自动匹配的优化策略规则列表，JSON 数组格式",
    )

    manual_rules = models.JSONField(
        default=list,
        verbose_name="手动规则表",
        help_text="用户手动指定的优化策略规则列表，JSON 数组格式",
    )

    is_manual_rules = models.IntegerField(
        choices=ManualRulesStatus.choices,
        default=ManualRulesStatus.NO,
        verbose_name="是否手动设置规则",
    )

    manual_rules_expiry = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="手动规则有效期",
        help_text="用户手动设置规则的到期时间；null 表示不限（永久有效）",
    )

    rule_updated_today = models.BooleanField(
        default=False,
        verbose_name="当日是否更新",
        help_text="当日是否已重新匹配过优化策略规则",
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
        db_table = "sp_ad_optimization_strategy"
        verbose_name = "SP 广告优化策略"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        unique_together = (("campaign_id", "profile_id", "targeting_type"),)
        indexes = [
            models.Index(fields=["campaign_id", "profile_id"]),
        ]

    def __str__(self) -> str:
        return (
            f"SpAdOptimizationStrategy<"
            f"campaign={self.campaign_id}, "
            f"profile={self.profile_id}, "
            f"targeting={self.targeting_type}>"
        )
