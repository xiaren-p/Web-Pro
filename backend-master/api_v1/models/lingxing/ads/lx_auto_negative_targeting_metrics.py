"""自动广告否定定向指标表（lx_auto_negative_targeting_metrics，managed=False，按天存储）。"""
from django.db import models


class LxAutoNegativeTargetingMetrics(models.Model):
    """自动广告否定定向指标表（按天存储）。

    所有指标字段均与数据库 VARCHAR 类型对应，数值转换在 Service 层完成。
    查询时始终过滤 campaign_id + profile_id，确保跨店铺数据隔离。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    target_id = models.CharField(
        max_length=100,
        verbose_name="否定定向 ID",
    )

    campaign_id = models.CharField(
        max_length=100,
        verbose_name="所属广告活动 ID",
    )

    profile_id = models.CharField(
        max_length=100,
        verbose_name="店铺 Profile ID",
    )

    sales = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="广告销售额",
    )

    orders = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="广告订单数",
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
        verbose_name="更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_auto_negative_targeting_metrics"
        verbose_name = "自动广告否定定向指标"
        verbose_name_plural = "自动广告否定定向指标"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"LxAutoNegativeTargetingMetrics<{self.target_id}@{self.timestamp}>"
