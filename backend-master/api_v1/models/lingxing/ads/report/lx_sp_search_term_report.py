"""SP 用户搜索词报表表（lx_sp_search_term_report）。"""
from django.db import models


class LxSpSearchTermReport(models.Model):
    """SP 用户搜索词报表表（领星 → 广告 → 报表 → SP 用户搜索词报表）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    query = models.CharField(
        max_length=500,
        default="",
        verbose_name="搜索词",
    )

    target_id = models.BigIntegerField(
        verbose_name="投放 ID",
    )

    match_type = models.CharField(
        max_length=20,
        default="",
        verbose_name="匹配类型",
    )

    target_text = models.CharField(
        max_length=500,
        default="",
        verbose_name="投放的内容",
    )

    ad_group_id = models.BigIntegerField(
        verbose_name="广告组 ID",
    )

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="亚马逊店铺数字 ID",
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
        verbose_name="直接成交销量",
    )

    class Meta:
        db_table = "lx_sp_search_term_report"
        verbose_name = "SP 用户搜索词报表"
        verbose_name_plural = verbose_name
        ordering = ["-report_date"]
        unique_together = (("target_id", "query", "profile_id", "report_date"),)
        indexes = [
            models.Index(fields=["campaign_id", "profile_id"]),
            models.Index(fields=["ad_group_id"]),
            models.Index(fields=["report_date"]),
        ]

    def __str__(self) -> str:
        return f"LxSpSearchTermReport<q={self.query[:30]}, {self.report_date}>"
