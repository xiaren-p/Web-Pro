"""自动广告否定定向基础信息表（lx_auto_negative_targeting_info，managed=False）。"""
from django.db import models


class NegativeExpType(models.TextChoices):
    """否定定向类型枚举。"""

    ASIN = "asin", "否定ASIN"
    BRAND = "brand", "否定品牌"


class LxAutoNegativeTargetingInfo(models.Model):
    """自动广告否定定向基础信息表。

    每行对应一个自动广告否定定向条款，以 target_id + campaign_id + profile_id
    三元唯一标识。exp_type 区分否定 ASIN / 否定品牌，exp_value 存储具体值。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    target_id = models.CharField(
        max_length=100,
        verbose_name="否定定向 ID",
    )

    ad_group_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="所属广告组 ID",
    )

    portfolio_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
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
        null=True,
        blank=True,
        verbose_name="有效状态",
        help_text="enabled / archived",
    )

    service_status = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="服务状态·平台层面",
    )

    exp_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="否定类型",
        help_text="asin / brand",
    )

    exp_value = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="否定值",
        help_text="ASIN 编码 或 品牌名称",
    )

    asin_price = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="商品售价",
    )

    asin_stars = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="商品评分",
    )

    asin_review_count = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="评论数量",
    )

    asin_title = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        verbose_name="商品标题",
    )

    targeting_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="投放类型",
        help_text="auto",
    )

    created_at = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="创建时间",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_auto_negative_targeting_info"
        verbose_name = "自动广告否定定向基础信息"
        verbose_name_plural = "自动广告否定定向基础信息"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"LxAutoNegativeTargetingInfo<{self.target_id}>"
