"""Nextcloud 群组镜像模型（nc_group）。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class NcGroupType(models.TextChoices):
    """NC 群组类型枚举。"""

    DEPT = "DEPT", "部门群组"
    DEPT_ADMIN = "DEPT_ADMIN", "部门管理员群组"
    COMPANY_SHARED = "COMPANY_SHARED", "公司共享群组"
    CUSTOM = "CUSTOM", "自定义群组"


class NcGroup(TimeStampedModel):
    """Nextcloud 群组镜像：与 NC group_id 1:1 对应，作为权限规则的连接锚点。

    双群组设计：每个部门对应两条记录——
      - group_type=DEPT       → 普通成员群组（仅读权限，permissions=1）
      - group_type=DEPT_ADMIN → 管理员群组（全权限，permissions=31）
    NC 对同一用户所属的多个群组权限取并集（最高优先），
    故 DEPT_ADMIN 用户实际拥有完整访问权限。
    """

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

    dept = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nc_groups",
        verbose_name="关联部门",
        help_text="DEPT/DEPT_ADMIN 类型时绑定对应部门；同一部门允许两条记录（DEPT + DEPT_ADMIN）",
    )

    folder_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="NC Group Folder ID",
        help_text="create_group_folder 返回的 folder id；DEPT_ADMIN 群组此字段为空，以对应 DEPT 群组的 folder_id 为准",
    )

    class Meta:
        verbose_name = "NC 群组"
        verbose_name_plural = "NC 群组"
        ordering = ("id",)
        unique_together = (("dept", "group_type"),)

    def __str__(self) -> str:
        return f"{self.name}({self.code})"
