"""广告活动指标模型（lx_campaign_metrics，managed=False）。"""
from django.db import models


class LxCampaignMetrics(models.Model):
    """广告活动指标表（按天存储，查询时按日期范围聚合）。

    profile_id 与 campaign_id + timestamp 构成复合唯一索引，
    查询和聚合均必须同时过滤 campaign_id + profile_id，
    防止不同店铺相同 campaign_id 导致指标混汇。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="主键",
    )

    campaign_id = models.CharField(
        max_length=100,
        verbose_name="广告 ID",
    )

    profile_id = models.CharField(
        max_length=100,
        verbose_name="店铺 Profile ID",
    )

    top_of_search_impression_share = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default="",
        verbose_name="搜索首位展示份额 (IS)",
    )

    sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="广告销售额",
    )

    direct_sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="直接销售额",
    )

    orders = models.IntegerField(
        default=0,
        verbose_name="广告订单数",
    )

    direct_orders = models.IntegerField(
        default=0,
        verbose_name="直接订单数",
    )

    ad_units = models.IntegerField(
        default=0,
        verbose_name="广告销量",
    )

    impressions = models.IntegerField(
        default=0,
        verbose_name="曝光量",
    )

    clicks = models.IntegerField(
        default=0,
        verbose_name="点击次数",
    )

    cpc = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="CPC",
    )

    spends = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="广告花费",
    )

    timestamp = models.DateField(
        verbose_name="数据日期",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_campaign_metrics"
        verbose_name = "广告活动指标表"
        verbose_name_plural = "广告活动指标表"
        unique_together = (("campaign_id", "profile_id", "timestamp"),)

