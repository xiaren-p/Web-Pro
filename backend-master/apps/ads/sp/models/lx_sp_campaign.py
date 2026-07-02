"""SP 广告活动基础数据表（lx_sp_campaign）。"""
from django.db import models


class SpCampaignTargetingType(models.TextChoices):
    """SP 广告活动投放类型枚举。"""

    AUTO = "auto", "自动投放"
    MANUAL = "manual", "手动投放"


class LxSpCampaign(models.Model):
    """SP 广告活动基础数据表（领星 → 广告 → 基础数据 → SP 广告活动）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 Profile ID",
    )

    name = models.CharField(
        max_length=255,
        default="",
        verbose_name="广告活动名称",
    )

    campaign_type = models.CharField(
        max_length=100,
        default="",
        verbose_name="广告活动类型",
        help_text="如 sponsoredProducts",
    )

    targeting_type = models.CharField(
        max_length=20,
        choices=SpCampaignTargetingType.choices,
        default=SpCampaignTargetingType.AUTO,
        verbose_name="投放类型",
    )

    premium_bid_adjustment = models.IntegerField(
        default=0,
        verbose_name="溢价报价调整",
    )

    daily_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="每日预算",
    )

    start_date = models.CharField(
        max_length=50,
        default="",
        verbose_name="起始日期",
    )

    end_date = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="结束日期",
    )

    state = models.CharField(
        max_length=50,
        default="",
        verbose_name="状态",
    )

    serving_status = models.CharField(
        max_length=100,
        default="",
        verbose_name="服务状态",
    )

    bidding = models.JSONField(
        null=True,
        blank=True,
        verbose_name="竞价策略",
        help_text="JSON：strategy / adjustments",
    )

    portfolio_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="广告组合 ID",
    )

    tags = models.JSONField(
        null=True,
        blank=True,
        verbose_name="标签信息",
        help_text="数组：[{parent, child}, ...]",
    )

    creation_date = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="创建时间（毫秒时间戳）",
    )

    last_updated_date = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="最后更新时间（毫秒时间戳）",
    )

    class Meta:
        db_table = "lx_sp_campaign"
        verbose_name = "SP 广告活动"
        verbose_name_plural = "SP 广告活动列表"
        ordering = ["-creation_date"]
        unique_together = (("campaign_id", "profile_id"),)

    def __str__(self) -> str:
        return f"LxSpCampaign<{self.campaign_id}> {self.name}"
