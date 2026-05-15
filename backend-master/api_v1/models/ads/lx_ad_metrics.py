"""广告投放指标模型（lx_ad_metrics，managed=False，按天存储）。"""
from django.db import models


class LxAdMetrics(models.Model):
    """广告投放（Product Ad）指标表，按天聚合存储。

    查询时始终同时过滤 ad_id + campaign_id + profile_id，
    确保跨店同名广告的数据隔离。
    注意：该表无 ad_group_id 字段，
    聚合时通过 ad_id 列表（来自 lx_ad_info）进行关联查询。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    ad_id = models.CharField(
        max_length=100,
        verbose_name="广告投放 ID",
    )

    campaign_id = models.CharField(
        max_length=100,
        verbose_name="所属广告活动 ID",
    )

    profile_id = models.CharField(
        max_length=100,
        verbose_name="店铺 Profile ID",
    )

    sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
        verbose_name="广告销售额",
    )

    direct_sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
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
        verbose_name="广告销量（件数）",
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
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="CPC",
        help_text="原始存储值，计算时以 spends/clicks 为准",
    )

    spends = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
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
        db_table = "lx_ad_metrics"
        verbose_name = "广告投放指标表"
        verbose_name_plural = "广告投放指标表"
        unique_together = (("ad_id", "campaign_id", "profile_id", "timestamp"),)

    def __str__(self) -> str:
        return f"LxAdMetrics<{self.ad_id}@{self.timestamp}>"
