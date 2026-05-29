"""否定关键词指标表（lx_negative_keyword_metrics，managed=False，按天存储）。"""
from django.db import models


class LxNegativeKeywordMetrics(models.Model):
    """否定关键词指标表（按天存储）。

    指标字段使用原生数值类型（decimal / int），可直接使用 Django ORM Sum() 聚合。
    查询时始终过滤 campaign_id + profile_id，确保跨店铺数据隔离。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    keyword_id = models.CharField(
        max_length=100,
        verbose_name="否定关键词 ID",
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
        default=0,
        verbose_name="广告销售额",
    )

    orders = models.IntegerField(
        default=0,
        verbose_name="广告订单数",
    )

    spends = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="花费",
    )

    timestamp = models.DateField(
        verbose_name="数据日期",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_negative_keyword_metrics"
        verbose_name = "否定关键词指标"
        verbose_name_plural = "否定关键词指标"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"LxNegativeKeywordMetrics<{self.keyword_id}@{self.timestamp}>"
