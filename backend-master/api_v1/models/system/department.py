"""部门模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class Department(TimeStampedModel):
    """部门表：父子树结构。"""

    name = models.CharField(
        max_length=100,
        verbose_name="部门名称",
    )

    code = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="部门编号",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父部门",
    )

    order_num = models.IntegerField(
        default=0,
        verbose_name="排序号",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    class Meta:
        verbose_name = "部门"
        verbose_name_plural = "部门"
        ordering = ("order_num", "id")

    def __str__(self) -> str:
        return self.name

