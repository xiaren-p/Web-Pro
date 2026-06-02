"""广告分时策略命中记录表（ad_time_pricing_hit）。"""
from django.db import models


class TimePricingHitStatus(models.IntegerChoices):
    """是否正在分时枚举。"""

    YES = 1, "是"
    NO = 0, "否"


class ManualRulesStatus(models.IntegerChoices):
    """是否手动设置规则枚举。"""

    YES = 1, "是"
    NO = 0, "否"


class AdTimePricingHit(models.Model):
    """广告分时策略命中记录表。

    记录每条广告（ad_id + profile_id）的分时策略命中结果。
    """

    ad_id = models.BigIntegerField(
        verbose_name="广告 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 Profile ID",
    )

    hit_auto_bid_rules = models.CharField(
        max_length=255,
        default="",
        verbose_name="命中自动竞价规则",
    )

    hit_time_pricing_rules = models.CharField(
        max_length=500,
        default="",
        verbose_name="命中分时策略规则",
        help_text="命中策略的名称，多条用逗号分隔",
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
        unique_together = (("ad_id", "profile_id"),)
        indexes = [
            models.Index(fields=["ad_id", "profile_id"]),
            models.Index(fields=["is_time_pricing"]),
        ]

    def __str__(self) -> str:
        return f"AdTimePricingHit<ad={self.ad_id}, profile={self.profile_id}>"
