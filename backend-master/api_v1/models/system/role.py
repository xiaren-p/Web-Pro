"""角色模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class DataScope(models.IntegerChoices):
    """角色数据权限范围枚举。"""

    ALL = 1, "全部数据"
    DEPT_AND_CHILDREN = 2, "部门及子部门数据"
    DEPT_ONLY = 3, "本部门数据"
    SELF_ONLY = 4, "仅本人数据"


class Role(TimeStampedModel):
    """角色表：承载菜单权限与数据范围。"""

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="角色编码",
    )

    name = models.CharField(
        max_length=50,
        verbose_name="角色名称",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否启用",
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

    data_scope = models.IntegerField(
        choices=DataScope.choices,
        default=DataScope.ALL,
        verbose_name="数据权限范围",
    )

    menus = models.ManyToManyField(
        "Menu",
        blank=True,
        related_name="roles",
        verbose_name="菜单列表",
    )

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = "角色"
        ordering = ("order_num", "id")

    def __str__(self) -> str:
        return self.name

