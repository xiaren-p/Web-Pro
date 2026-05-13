"""广告货币汇率配置模型（lx_currency_rates，managed=False）。"""
from django.db import models


class LxCurrencyRates(models.Model):
    """亚马逊广告货币汇率配置（只读镜像）。

    rate 为实际使用汇率，目标货币为人民币（CNY），
    即 1 单位本地货币 = rate 人民币。
    货币到国家的映射由 currency_icon 表负责，本表仅存汇率数据。
    """

    id = models.BigAutoField(
        primary_key=True,
    )

    code = models.CharField(
        max_length=20,
        verbose_name="货币代码",
    )

    icon = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="货币符号",
    )

    name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="货币名称",
    )

    target_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="目标货币代码",
    )

    target_icon = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="目标货币符号",
    )

    rate = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        null=True,
        blank=True,
        verbose_name="实际使用汇率（目标：人民币）",
    )

    is_cny = models.SmallIntegerField(
        default=0,
        verbose_name="是否人民币",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_currency_rates"
        verbose_name = "货币汇率配置"
        verbose_name_plural = "货币汇率配置"

    def __str__(self) -> str:
        return f"LxCurrencyRates<{self.code}>"
