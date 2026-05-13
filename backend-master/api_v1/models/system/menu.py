"""菜单模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class MenuType(models.IntegerChoices):
    """菜单节点类型枚举。"""

    DIRECTORY = 1, "目录"
    MENU = 2, "菜单"
    BUTTON = 3, "按钮"
    EXTERNAL = 4, "外链"


class Menu(TimeStampedModel):
    """后台菜单与权限节点。"""

    name = models.CharField(
        max_length=100,
        verbose_name="菜单名称",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父菜单",
    )

    type = models.IntegerField(
        choices=MenuType.choices,
        default=MenuType.MENU,
        verbose_name="菜单类型",
    )

    route_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="路由名称 name",
    )

    path = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="路由路径",
    )

    component = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="前端组件路径",
    )

    perms = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="权限标识",
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="图标标识",
    )

    order_num = models.IntegerField(
        default=0,
        verbose_name="排序号",
    )

    visible = models.BooleanField(
        default=True,
        verbose_name="是否可见",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    class Meta:
        verbose_name = "菜单"
        verbose_name_plural = "菜单"
        ordering = ("order_num", "id")

    def __str__(self) -> str:
        return self.name

