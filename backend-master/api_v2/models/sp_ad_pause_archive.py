"""SP 广告投放暂停与归档操作记录表（sp_ad_pause_archive）。

记录自动/手动规则对广告活动、定位组、关键词、商品投放的暂停和归档操作。
"""
from django.db import models

from api_v2.models.sp_bid_adjustment import ExecutionStatusChoices


class PauseArchiveExecutionType(models.TextChoices):
    """暂停/归档执行类型枚举。"""

    PAUSE = "PAUSE", "暂停"
    ARCHIVE = "ARCHIVE", "归档"


class PauseArchiveEntityType(models.TextChoices):
    """投放实体类型枚举。"""

    CAMPAIGN = "campaign", "广告活动"
    TARGETING = "targeting", "定位组"
    KEYWORD = "keyword", "关键词"
    PRODUCT_TARGETING = "product_targeting", "商品投放"


class SpAdPauseArchive(models.Model):
    """SP 广告投放暂停与归档操作记录表。

    target_id 与 keyword_id 互斥：有定位组/商品投放时无关键词，有关键词时无定位组/商品投放。
    campaign 维度操作时三者均为空。
    """

    campaign_id = models.BigIntegerField(
        verbose_name="广告活动 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 ID",
    )

    target_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="定位组 / 商品投放 ID",
        help_text="与 keyword_id 互斥，只能存在一个",
    )

    keyword_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="关键词 ID",
        help_text="与 target_id 互斥，只能存在一个",
    )

    entity_type = models.CharField(
        max_length=30,
        choices=PauseArchiveEntityType.choices,
        verbose_name="实体类型",
        help_text="标识本次操作对应的投放实体维度",
    )

    execution_type = models.CharField(
        max_length=20,
        choices=PauseArchiveExecutionType.choices,
        verbose_name="执行类型",
        help_text="暂停（PAUSE）或归档（ARCHIVE）",
    )

    auto_rule_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="自动竞价规则 ID",
        help_text="自动/手动规则命中时写入关联的规则 ID",
    )

    execution_status = models.CharField(
        max_length=20,
        choices=ExecutionStatusChoices.choices,
        default=ExecutionStatusChoices.PENDING,
        verbose_name="执行状态",
    )

    execution_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="执行时间",
        help_text="操作实际执行的时间",
    )

    msg = models.TextField(
        default="",
        blank=True,
        verbose_name="执行日志回写",
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
        db_table = "sp_ad_pause_archive"
        verbose_name = "SP 广告暂停/归档操作记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign_id", "profile_id"]),
            models.Index(fields=["execution_type"]),
            models.Index(fields=["execution_status"]),
            models.Index(fields=["execution_time"]),
        ]

    def __str__(self) -> str:
        if self.keyword_id:
            item = f"keyword={self.keyword_id}"
        elif self.target_id:
            item = f"target={self.target_id}"
        else:
            item = f"campaign={self.campaign_id}"
        return f"SpAdPauseArchive<{item}, {self.execution_type}>"
