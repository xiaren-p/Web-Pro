"""岗位模型：承载系统菜单权限，替代原 Role 模型（position.py）。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class Position(TimeStampedModel):
    """岗位表：预定义的权限套餐，用户按 admin_level 路由后按需分配岗位。"""

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="岗位编码",
    )

    name = models.CharField(
        max_length=50,
        verbose_name="岗位名称",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    is_builtin = models.BooleanField(
        default=False,
        verbose_name="是否内置",
        help_text="内置岗位不可删除，如 sys_admin",
    )

    remark = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
    )

    order_num = models.IntegerField(
        default=0,
        verbose_name="排序号",
    )

    menus = models.ManyToManyField(
        "Menu",
        blank=True,
        related_name="positions",
        verbose_name="菜单列表",
    )

    class Meta:
        verbose_name = "岗位"
        verbose_name_plural = "岗位"
        ordering = ("order_num", "id")

    def __str__(self) -> str:
        return self.name
