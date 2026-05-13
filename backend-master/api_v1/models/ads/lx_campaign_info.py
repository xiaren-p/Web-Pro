"""广告活动基础模型（lx_campaign_info，managed=False）。"""
from django.db import models


class LxCampaignInfo(models.Model):
    """广告活动基础表。

    主键为自增 id，campaign_id + profile_id 构成复合唯一索引，
    解决不同店铺可能出现相同 campaign_id 的极小概率冲突问题。
    tags 字段由 varchar(255) 升级为 text。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    campaign_id = models.CharField(
        max_length=100,
        verbose_name="广告活动 ID",
    )

    name = models.CharField(
        max_length=255,
        default="",
        verbose_name="广告名字",
    )

    state = models.CharField(
        max_length=50,
        default="",
        verbose_name="有效状态",
    )

    sponsored_type = models.CharField(
        max_length=50,
        default="",
        verbose_name="广告类型",
    )

    service_status = models.CharField(
        max_length=50,
        default="",
        verbose_name="服务状态",
    )

    portfolio_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="广告组合 ID",
    )

    bidding_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="竞价策略",
    )

    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="预算",
    )

    last_over_budget_at = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="超预算时间",
    )

    start_date = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="开始日期",
    )

    tags = models.TextField(
        null=True,
        blank=True,
        verbose_name="标签",
    )

    profile_id = models.CharField(
        max_length=100,
        default="",
        verbose_name="店铺 Profile ID",
    )

    store_id = models.CharField(
        max_length=100,
        default="",
        verbose_name="店铺 ID",
    )

    targeting_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="定向类型",
        help_text="AUTO / MANUAL",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_campaign_info"
        verbose_name = "广告活动基础表"
        verbose_name_plural = "广告活动基础表"
        unique_together = (("campaign_id", "profile_id"),)

