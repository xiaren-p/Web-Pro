"""SP 否定投放基础数据表（lx_sp_negative_target）。"""
from django.db import models


class NegativeTargetType(models.TextChoices):
    """SP 否定投放类型枚举。"""

    NEGATIVE_KEYWORD = "negativeKeyword", "否定关键词"
    NEGATIVE_ASIN = "negativeAsin", "否定 ASIN"
    NEGATIVE_BRAND = "negativeBrand", "否定品牌"


class LxSpNegativeTarget(models.Model):
    """SP 否定投放基础数据表（领星 → 广告 → 基础数据 → SP 否定投放）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    ad_group_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="广告组 ID",
    )

    target_id = models.BigIntegerField(
        verbose_name="否定投放 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 Profile ID",
    )

    negative_type = models.CharField(
        max_length=30,
        choices=NegativeTargetType.choices,
        default=NegativeTargetType.NEGATIVE_KEYWORD,
        verbose_name="否定类型",
    )

    negative_text = models.CharField(
        max_length=500,
        default="",
        verbose_name="否定内容",
        help_text="否定关键词文本 / 否定 ASIN / 否定品牌名称",
    )

    negative_match_type = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="否定匹配方式",
        help_text="negativeExact / negativePhrase；否定 ASIN/品牌时为空字符串",
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
        db_table = "lx_sp_negative_target"
        verbose_name = "SP 否定投放"
        verbose_name_plural = "SP 否定投放列表"
        ordering = ["-creation_date"]
        unique_together = (("target_id", "profile_id"),)

    def __str__(self) -> str:
        return f"LxSpNegativeTarget<{self.target_id}> {self.negative_type}"
