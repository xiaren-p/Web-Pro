"""货币图标配置模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class CurrencyIcon(TimeStampedModel):
    """货币图标配置。"""

    id = models.AutoField(primary_key=True)

    country = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="国家",
    )

    code = models.CharField(
        max_length=50,
        verbose_name="货币代码",
    )

    icon = models.CharField(
        max_length=50,
        verbose_name="货币标识",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="名字",
    )

    class Meta:
        db_table = "currency_icon"
        verbose_name = "货币图标配置"
        verbose_name_plural = "货币图标配置"

    def __str__(self) -> str:
        return f"{self.country} - {self.code}"

