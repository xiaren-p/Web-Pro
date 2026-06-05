"""广告分时策略命中记录表（ad_time_pricing_hit）。

以 LxSpCampaign 的 (campaign_id, profile_id) 为粒度，
记录广告活动命中分时策略的状态与时间。
"""
from django.db import models

from api_v1.models.lingxing.ads.basic.lx_sp_campaign import SpCampaignTargetingType


class TimePricingHitStatus(models.IntegerChoices):
    """是否正在分时。"""

    YES = 1, "是"
    NO = 0, "否"


class ManualRulesStatus(models.IntegerChoices):
    """是否手动设置规则。"""

    YES = 1, "是"
    NO = 0, "否"


class AdTimePricingHit(models.Model):
    """广告分时策略命中记录表。"""

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

    # ── 命中的分时策略规则 ID ──────────────────────────────────────────────

    hit_time_pricing_rules = models.CharField(
        max_length=500,
        default="",
        verbose_name="命中分时策略规则",
        help_text="命中的策略 ID（单条）",
    )

    # ── 分时状态 ──────────────────────────────────────────────────────────

    is_time_pricing = models.IntegerField(
        choices=TimePricingHitStatus.choices,
        default=TimePricingHitStatus.NO,
        verbose_name="是否正在分时",
    )

    time_start = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="分时开始时间",
        help_text="本次分时生效的开始时间（当地站点时间）",
    )

    time_end = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="分时结束时间",
        help_text="本次分时结束的回调时间（当地站点时间）",
    )

    time_start_cn = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="分时开始时间-中国",
        help_text="本次分时生效的开始时间（Asia/Shanghai）",
    )

    time_end_cn = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="分时结束时间-中国",
        help_text="本次分时结束的回调时间（Asia/Shanghai）",
    )

    # ── 用户手动规则 ──────────────────────────────────────────────────────

    is_manual_rules = models.IntegerField(
        choices=ManualRulesStatus.choices,
        default=ManualRulesStatus.NO,
        verbose_name="是否手动设置规则",
    )

    manual_rule_id = models.CharField(
        max_length=500,
        default="",
        verbose_name="用户设置规则的 ID",
        help_text="用户手动指定的规则 ID",
    )

    # ── 当日规则更新标记 ──────────────────────────────────────────────────

    rule_updated_today = models.BooleanField(
        default=False,
        verbose_name="当日规则是否更新",
        help_text="当日是否已重新匹配过规则",
    )

    # ── 回调状态 ──────────────────────────────────────────────────────────

    is_callback = models.IntegerField(
        choices=TimePricingHitStatus.choices,
        default=TimePricingHitStatus.NO,
        verbose_name="是否回调",
        help_text="该条记录是否已执行回调",
    )

    # ── 时间戳 ────────────────────────────────────────────────────────────

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
