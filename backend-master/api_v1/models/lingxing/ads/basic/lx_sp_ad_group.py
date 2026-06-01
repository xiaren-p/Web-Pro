"""SP 广告组基础数据表（lx_sp_ad_group）。"""
from django.db import models


class LxSpAdGroup(models.Model):
    """SP 广告组基础数据表（领星 → 广告 → 基础数据 → SP 广告组）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    ad_group_id = models.BigIntegerField(
        verbose_name="广告组 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 Profile ID",
    )

    name = models.CharField(
        max_length=255,
        default="",
        verbose_name="广告组名称",
    )

    default_bid = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="默认竞价",
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

    bid_optimization = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="优化建议",
        help_text="如 clicks",
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
        db_table = "lx_sp_ad_group"
        verbose_name = "SP 广告组"
        verbose_name_plural = "SP 广告组列表"
        ordering = ["-creation_date"]
        unique_together = (("ad_group_id", "profile_id"),)

    def __str__(self) -> str:
        return f"LxSpAdGroup<{self.ad_group_id}> {self.name}"
