"""否定关键词基础信息表（lx_negative_keyword_info，managed=False）。"""
from django.db import models


class NegativeMatchType(models.TextChoices):
    """否定关键词匹配方式枚举。"""

    NEGATIVE_EXACT = "negativeExact", "否定精准"
    NEGATIVE_PHRASE = "negativePhrase", "否定词组"


class LxNegativeKeywordInfo(models.Model):
    """否定关键词基础信息表。

    每行对应一个否定关键词，以 keyword_id + campaign_id + profile_id 三元唯一标识。
    match_type 区分否定精准（negativeExact）与否定词组（negativePhrase）。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    keyword_id = models.CharField(
        max_length=100,
        verbose_name="否定关键词 ID",
    )

    keyword_text = models.CharField(
        max_length=500,
        verbose_name="否定关键词文本",
    )

    match_type = models.CharField(
        max_length=50,
        verbose_name="匹配方式",
        help_text="negativeExact / negativePhrase",
    )

    portfolio_id = models.CharField(
        max_length=100,
        verbose_name="所属广告组合 ID",
    )

    campaign_id = models.CharField(
        max_length=100,
        verbose_name="所属广告活动 ID",
    )

    profile_id = models.CharField(
        max_length=100,
        verbose_name="店铺 Profile ID",
    )

    state = models.CharField(
        max_length=50,
        verbose_name="有效状态",
        help_text="enabled / archived",
    )

    service_status = models.CharField(
        max_length=100,
        verbose_name="服务状态·平台层面",
    )

    creation_date = models.CharField(
        max_length=50,
        verbose_name="创建时间",
    )

    targeting_mark = models.JSONField(
        null=True,
        blank=True,
        verbose_name="定向标记",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_negative_keyword_info"
        verbose_name = "否定关键词基础信息"
        verbose_name_plural = "否定关键词基础信息"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"LxNegativeKeywordInfo<{self.keyword_text}>"
