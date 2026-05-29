"""自动投放定向条款指标模型（lx_auto_targeting_metrics，managed=False，按天存储）。"""
from django.db import models


class LxAutoTargetingMetrics(models.Model):
    """自动投放定向条款指标表（按天存储）。

    所有指标字段均与数据库 VARCHAR 类型对应，数值转换在 Service 层完成。
    查询时始终过滤 campaign_id + profile_id，确保跨店铺数据隔离。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    target_id = models.CharField(
        max_length=100,
        verbose_name="定向条款 ID",
    )

    campaign_id = models.CharField(
        max_length=100,
        verbose_name="所属广告活动 ID",
    )

    profile_id = models.CharField(
        max_length=100,
        verbose_name="店铺 Profile ID",
    )

    top_of_search_impression_share = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="搜索结果首位展示率（IS）",
    )

    searchrank = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="搜索排名",
    )

    month_searchs = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="月搜索量",
    )

    sales = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="广告销售额",
    )

    direct_sales = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="直接销售额",
    )

    orders = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="广告订单数",
    )

    direct_orders = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="直接订单数",
    )

    ad_units = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="广告销量",
    )

    impressions = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="曝光量",
    )

    clicks = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="点击次数",
    )

    cpc = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="单次点击费用（CPC）",
    )

    spends = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="花费",
    )

    timestamp = models.DateField(
        verbose_name="数据日期",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=False,
        verbose_name="最后更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_auto_targeting_metrics"
        verbose_name = "自动投放定向条款指标"
        verbose_name_plural = "自动投放定向条款指标"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"LxAutoTargetingMetrics<{self.target_id}@{self.timestamp}>"
