"""广告账号基础表（lx_ads_profile）。"""
from django.db import models


class AdsProfileStatus(models.IntegerChoices):
    """广告账号启用状态枚举。"""

    DISABLED = 0, "禁用"
    ENABLED = 1, "启用"


class AdsProfileType(models.TextChoices):
    """广告账号类型枚举。"""

    SP = "sp", "Sponsored Products"
    SB = "sb", "Sponsored Brands"
    SD = "sd", "Sponsored Display"
    DSP = "dsp", "Demand-Side Platform"


class LxAdsProfile(models.Model):
    """广告账号基础表（领星 → 广告 → 基础数据 → 广告账号列表）。"""

    profile_id = models.BigIntegerField(
        primary_key=True,
        verbose_name="广告 Profile ID",
    )

    sid = models.CharField(
        max_length=100,
        default="",
        verbose_name="店铺 ID",
    )

    name = models.CharField(
        max_length=255,
        default="",
        verbose_name="账号名称",
    )

    country_code = models.CharField(
        max_length=10,
        default="",
        verbose_name="国家代码",
    )

    currency_code = models.CharField(
        max_length=10,
        default="",
        verbose_name="货币代码",
    )

    type = models.CharField(
        max_length=20,
        choices=AdsProfileType.choices,
        default="",
        verbose_name="账号类型",
    )

    status = models.IntegerField(
        choices=AdsProfileStatus.choices,
        default=AdsProfileStatus.ENABLED,
        verbose_name="启用状态",
    )

    class Meta:
        db_table = "lx_ads_profile"
        verbose_name = "广告账号"
        verbose_name_plural = "广告账号列表"
        ordering = ["profile_id"]

    def __str__(self) -> str:
        return f"LxAdsProfile<{self.profile_id}> {self.name}"
