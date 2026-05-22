"""Nextcloud 群组镜像模型（nc_group）。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class NcGroupType(models.TextChoices):
    """NC 群组类型枚举。"""

    DEPT = "DEPT", "部门群组"
    COMPANY_SHARED = "COMPANY_SHARED", "公司共享群组"
    CUSTOM = "CUSTOM", "自定义群组"


class NcGroup(TimeStampedModel):
    """Nextcloud 群组镜像：与 NC group_id 1:1 对应，作为权限规则的连接锚点。"""

    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="NC 群组 ID",
        help_text="Nextcloud 中的 group_id，创建/同步时使用",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="显示名称",
    )

    group_type = models.CharField(
        max_length=20,
        choices=NcGroupType.choices,
        default=NcGroupType.CUSTOM,
        verbose_name="群组类型",
    )

    dept = models.OneToOneField(
        "Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nc_group",
        verbose_name="关联部门",
        help_text="仅 DEPT 类型时绑定对应部门",
    )

    folder_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="NC Group Folder ID",
        help_text="create_group_folder 返回的 folder id，用于后续 grant_group_folder 授权",
    )

    class Meta:
        verbose_name = "NC 群组"
        verbose_name_plural = "NC 群组"
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.name}({self.code})"
