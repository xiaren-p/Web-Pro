"""字典项模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel
from api_v1.models.system.dict_type import DictType


class DictItem(TimeStampedModel):
    """字典项表：同一字典下 value 唯一。"""

    dict_type = models.ForeignKey(
        DictType,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="所属字典类型",
    )

    label = models.CharField(
        max_length=100,
        verbose_name="显示文本",
    )

    value = models.CharField(
        max_length=100,
        verbose_name="实际值",
    )

    sort = models.IntegerField(
        default=0,
        verbose_name="排序号",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    tag_type = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="标签样式",
        help_text="Element Plus Tag type，用于前端渲染样式",
    )

    class Meta:
        verbose_name = "字典项"
        verbose_name_plural = "字典项"
        unique_together = (("dict_type", "value"),)
        ordering = ("sort", "id")

    def __str__(self) -> str:
        return f"{self.dict_type.code}:{self.label}"

