"""SP 关键词基础数据表（lx_sp_keyword）。"""
from django.db import models


class SpKeywordMatchType(models.TextChoices):
    """SP 关键词匹配类型枚举。"""

    EXACT = "exact", "精准匹配"
    BROAD = "broad", "广泛匹配"
    PHRASE = "phrase", "词组匹配"


class LxSpKeyword(models.Model):
    """SP 关键词基础数据表（领星 → 广告 → 基础数据 → SP 关键词）。"""

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

    keyword_id = models.BigIntegerField(
        verbose_name="关键词 ID",
    )

    keyword_text = models.CharField(
        max_length=500,
        default="",
        verbose_name="关键词文本",
    )

    bid = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="竞价",
    )

    state = models.CharField(
        max_length=50,
        default="",
        verbose_name="状态",
    )

    match_type = models.CharField(
        max_length=20,
        choices=SpKeywordMatchType.choices,
        default=SpKeywordMatchType.BROAD,
        verbose_name="匹配类型",
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
        db_table = "lx_sp_keyword"
        verbose_name = "SP 关键词"
        verbose_name_plural = "SP 关键词列表"
        ordering = ["-creation_date"]
        unique_together = (("keyword_id", "profile_id"),)

    def __str__(self) -> str:
        return f"LxSpKeyword<{self.keyword_id}> {self.keyword_text}"
