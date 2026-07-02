"""汇率表（lx_exchange_rate，managed=False）。"""
from django.db import models


class LxExchangeRate(models.Model):
    """汇率表（领星 → 基础数据 → 汇率）。"""

    date = models.CharField(
        max_length=10,
        default="",
        verbose_name="汇率年月",
        help_text="形如 2021-08",
    )

    code = models.CharField(
        max_length=10,
        default="",
        verbose_name="币种",
    )

    icon = models.CharField(
        max_length=10,
        default="",
        verbose_name="币种符号",
    )

    name = models.CharField(
        max_length=50,
        default="",
        verbose_name="币种名",
    )

    rate_org = models.CharField(
        max_length=20,
        default="1.0000",
        verbose_name="官方汇率",
        help_text="数据来源于中国银行官方汇率",
    )

    my_rate = models.CharField(
        max_length=20,
        default="1.0000",
        verbose_name="我的汇率",
        help_text="用户自定义汇率，系统优先使用该汇率数据",
    )

    update_time = models.CharField(
        max_length=30,
        default="",
        verbose_name="更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_exchange_rate"
        verbose_name = "汇率"
        verbose_name_plural = "汇率列表"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"LxExchangeRate<{self.code}, {self.date}>"
