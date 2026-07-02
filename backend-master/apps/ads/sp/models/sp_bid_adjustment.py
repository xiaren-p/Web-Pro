"""SP 广告商品投放调整记录表（sp_bid_adjustment）。

记录定位组 / 关键词 / 商品投放维度的竞价调整、暂停、启用操作。
"""
from django.db import models

from apps.ads.sp.models.ad_time_pricing_hit import TimePricingHitStatus


class ExecutionTypeChoices(models.TextChoices):
    """执行类型枚举（大写固定值）。"""

    TIME_PRICING_START = "TIME_PRICING_START", "分时开始"
    TIME_PRICING_CALLBACK = "TIME_PRICING_CALLBACK", "分时回调"
    BID_ADJUSTMENT = "BID_ADJUSTMENT", "竞价调整"
    BID_PAUSE = "BID_PAUSE", "竞价暂停"
    BID_ENABLE = "BID_ENABLE", "竞价启用"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT", "手动调整"


class PauseEntityTypeChoices(models.TextChoices):
    """暂停投放实体类型枚举（仅用于 BID_PAUSE 记录区分实体维度）。"""

    TARGETING = "targeting", "定位组"
    KEYWORD = "keyword", "关键词"
    PRODUCT_TARGETING = "product_targeting", "商品投放"


class AdjustmentStatusChoices(models.TextChoices):
    """调整状态枚举。"""

    PENDING = "PENDING", "待执行"
    SUCCESS = "SUCCESS", "成功"
    FAILED = "FAILED", "失败"


class ExecutionStatusChoices(models.TextChoices):
    """执行状态枚举。"""

    PENDING = "PENDING", "待执行"
    RUNNING = "RUNNING", "执行中"
    SUCCESS = "SUCCESS", "成功"
    FAILED = "FAILED", "失败"


class SpBidAdjustment(models.Model):
    """SP 广告商品投放调整记录表。

    target_id 与 keyword_id 互斥：有定位组时无关键词，有关键词时无定位组。
    """

    target_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="定位组 ID",
        help_text="与 keyword_id 互斥，只能存在一个",
    )

    keyword_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="关键词 ID",
        help_text="与 target_id 互斥，只能存在一个",
    )

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 ID",
    )

    execution_type = models.CharField(
        max_length=50,
        choices=ExecutionTypeChoices.choices,
        verbose_name="执行类型",
    )

    time_pricing_rule_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="分时规则 ID",
        help_text="分时策略命中时写入关联的策略 ID",
    )

    auto_rule_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="自动竞价规则 ID",
        help_text="自动竞价规则命中时写入关联的规则 ID",
    )

    is_time_pricing = models.IntegerField(
        choices=TimePricingHitStatus.choices,
        default=TimePricingHitStatus.NO,
        verbose_name="是否正在分时",
    )

    bid_before = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="调整前竞价",
    )

    bid_after = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="调整后竞价",
    )

    adjustment_status = models.CharField(
        max_length=20,
        choices=AdjustmentStatusChoices.choices,
        default=AdjustmentStatusChoices.PENDING,
        verbose_name="调整状态",
    )

    adjustment_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="调整时间",
    )

    execution_status = models.CharField(
        max_length=20,
        choices=ExecutionStatusChoices.choices,
        default=ExecutionStatusChoices.PENDING,
        verbose_name="执行状态",
    )

    msg = models.TextField(
        default="",
        blank=True,
        verbose_name="执行日志回写",
    )

    operator = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="操作人",
        help_text="用户手动操作时写入用户昵称；任务自动写入时留空",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        db_table = "sp_bid_adjustment"
        verbose_name = "SP 广告商品投放调整记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign_id", "profile_id"]),
            models.Index(fields=["execution_type"]),
            models.Index(fields=["execution_status"]),
            models.Index(fields=["adjustment_time"]),
            models.Index(fields=["keyword_id", "created_at"]),
            models.Index(fields=["target_id", "created_at"]),
        ]

    def __str__(self) -> str:
        item = f"target={self.target_id}" if self.target_id else f"keyword={self.keyword_id}"
        return f"SpBidAdjustment<{item}, campaign={self.campaign_id}>"
