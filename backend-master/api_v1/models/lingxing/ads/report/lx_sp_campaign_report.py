"""SP 广告活动报表表（lx_sp_campaign_report）。"""
from django.db import models


class LxSpCampaignReport(models.Model):
    """SP 广告活动报表表（领星 → 广告 → 报表 → SP 广告活动报表）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    targeting_type = models.CharField(
        max_length=20,
        default="",
        verbose_name="投放类型",
    )

    impressions = models.IntegerField(
        default=0,
        verbose_name="展示量",
    )

    clicks = models.IntegerField(
        default=0,
        verbose_name="点击量",
    )

    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="花费",
    )

    report_date = models.DateField(
        verbose_name="报表日期",
    )

    profile_id = models.BigIntegerField(
        verbose_name="亚马逊店铺数字 ID",
    )

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    same_orders = models.IntegerField(
        default=0,
        verbose_name="直接成交订单数",
    )

    orders = models.IntegerField(
        default=0,
        verbose_name="订单数",
    )

    same_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="直接成交销售额",
    )

    sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="销售额",
    )

    units = models.IntegerField(
        default=0,
        verbose_name="销量",
    )

    same_units = models.IntegerField(
        default=0,
        verbose_name="直接成交量",
    )

    class Meta:
        db_table = "lx_sp_campaign_report"
        verbose_name = "SP 广告活动报表"
        verbose_name_plural = verbose_name
        ordering = ["-report_date"]
        unique_together = (("campaign_id", "profile_id", "report_date"),)
        indexes = [
            models.Index(fields=["campaign_id", "profile_id"]),
            models.Index(fields=["report_date"]),
        ]

    def __str__(self) -> str:
        return f"LxSpCampaignReport<c={self.campaign_id}, {self.report_date}>"
