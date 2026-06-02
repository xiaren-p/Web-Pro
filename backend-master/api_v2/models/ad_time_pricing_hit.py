"""广告策略命中记录表（ad_time_pricing_hit）。"""
from django.db import models

from api_v1.models.lingxing.ads.basic.lx_sp_campaign import SpCampaignTargetingType


class TimePricingHitStatus(models.IntegerChoices):
    """是否正在分时枚举。"""

    YES = 1, "是"
    NO = 0, "否"


class ManualRulesStatus(models.IntegerChoices):
    """是否手动设置规则枚举。"""

    YES = 1, "是"
    NO = 0, "否"


class AdTimePricingHit(models.Model):
    """广告策略命中记录表。

    以 LxSpCampaign 的 (campaign_id, profile_id) 为粒度，记录广告活动是否命中分时策略。
    """

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

    timezone = models.CharField(
        max_length=50,
        default="",
        verbose_name="时区",
    )

    hit_auto_bid_rules = models.CharField(
        max_length=255,
        default="",
        verbose_name="命中自动竞价规则",
        help_text="命中的自动竞价规则 ID（单条）",
    )

    hit_time_pricing_rules = models.CharField(
        max_length=500,
        default="",
        verbose_name="命中分时策略规则",
        help_text="命中的策略 ID（单条）",
    )

    is_time_pricing = models.IntegerField(
        choices=TimePricingHitStatus.choices,
        default=TimePricingHitStatus.NO,
        verbose_name="是否正在分时",
    )

    default_bid_rules = models.JSONField(
        default=list,
        verbose_name="默认竞价规则",
        help_text="竞价规则字符串列表",
    )

    user_manual_bid_rules = models.JSONField(
        default=list,
        verbose_name="用户手动设置竞价规则",
        help_text="竞价规则字符串列表",
    )

    user_manual_time_rules = models.JSONField(
        default=list,
        verbose_name="用户手动设置分时规则",
        help_text="用户手动设置的分时规则字符串列表",
    )

    is_manual_rules = models.IntegerField(
        choices=ManualRulesStatus.choices,
        default=ManualRulesStatus.NO,
        verbose_name="是否手动设置规则",
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
        db_table = "ad_time_pricing_hit"
        verbose_name = "广告分时策略命中记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        unique_together = (("campaign_id", "profile_id"),)
        indexes = [
            models.Index(fields=["campaign_id", "profile_id"]),
        ]

    def __str__(self) -> str:
        return f"AdTimePricingHit<campaign={self.campaign_id}, profile={self.profile_id}>"
