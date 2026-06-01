"""SP 商品定位基础数据表（lx_sp_target）。"""
from django.db import models


class SpTargetExpressionType(models.TextChoices):
    """SP 商品定位表达式类型枚举。"""

    AUTO = "auto", "自动"
    MANUAL = "manual", "手动"


class LxSpTarget(models.Model):
    """SP 商品定位基础数据表（领星 → 广告 → 基础数据 → SP 商品定位）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    target_id = models.BigIntegerField(
        verbose_name="商品定位 ID",
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

    expression_type = models.CharField(
        max_length=20,
        choices=SpTargetExpressionType.choices,
        default=SpTargetExpressionType.AUTO,
        verbose_name="表达式类型",
    )

    expression = models.JSONField(
        null=True,
        blank=True,
        verbose_name="表达式",
        help_text='JSON 数组，如 [{"type": "asinAccessoryRelated"}]',
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

    serving_status = models.CharField(
        max_length=100,
        default="",
        verbose_name="服务状态",
    )

    resolved_expression = models.TextField(
        null=True,
        blank=True,
        verbose_name="已解析的表达式",
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
        db_table = "lx_sp_target"
        verbose_name = "SP 商品定位"
        verbose_name_plural = "SP 商品定位列表"
        ordering = ["-creation_date"]
        unique_together = (("target_id", "profile_id"),)

    def __str__(self) -> str:
        return f"LxSpTarget<{self.target_id}>"
