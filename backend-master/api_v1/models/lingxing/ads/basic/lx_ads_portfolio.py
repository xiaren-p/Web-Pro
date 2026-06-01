"""广告组合基础数据表（lx_ads_portfolio）。"""
from django.db import models


class PortfolioInBudgetStatus(models.IntegerChoices):
    """广告组合预算状态枚举。"""

    OVER = 0, "超出预算"
    IN = 1, "在范围内"


class LxAdsPortfolio(models.Model):
    """广告组合基础数据表（领星 → 广告 → 基础数据 → 广告组合）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    portfolio_id = models.BigIntegerField(
        verbose_name="广告组合 ID",
    )

    profile_id = models.BigIntegerField(
        verbose_name="店铺 Profile ID",
    )

    name = models.CharField(
        max_length=255,
        default="",
        verbose_name="广告组合名称",
    )

    budget = models.JSONField(
        null=True,
        blank=True,
        verbose_name="预算信息",
        help_text="JSON：amount / policy / startDate / endDate / currencyCode；null 表示无上限",
    )

    in_budget = models.IntegerField(
        choices=PortfolioInBudgetStatus.choices,
        default=PortfolioInBudgetStatus.IN,
        verbose_name="是否在预算范围内",
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
        db_table = "lx_ads_portfolio"
        verbose_name = "广告组合"
        verbose_name_plural = "广告组合列表"
        ordering = ["-creation_date"]
        unique_together = (("portfolio_id", "profile_id"),)

    def __str__(self) -> str:
        return f"LxAdsPortfolio<{self.portfolio_id}> {self.name}"
