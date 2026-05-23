"""Nextcloud 文件夹访问权限规则模型（nc_file_access_rule）。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class NcFileAccessRule(TimeStampedModel):
    """NC 群组与文件夹的权限绑定规则表。

    使用位图描述权限（与 NC OCS Share API permission 字段对齐）：
        READ=1  WRITE=2  CREATE=4  DELETE=8  SHARE=16
    组合示例：读写 = 1+2=3，全权 = 31。
    """

    # 权限位常量（供业务层直接引用）
    PERM_READ: int = 1
    PERM_WRITE: int = 2
    PERM_CREATE: int = 4
    PERM_DELETE: int = 8
    PERM_SHARE: int = 16
    PERM_FULL: int = 31  # READ + WRITE + CREATE + DELETE + SHARE

    nc_group = models.ForeignKey(
        "NcGroup",
        on_delete=models.CASCADE,
        related_name="file_rules",
        verbose_name="NC 群组",
    )

    nc_path = models.CharField(
        max_length=500,
        verbose_name="NC 子路径",
        help_text="从 Group Folder 挂载点开始的子路径，如 '技术部/机密文档' 或 '技术部'；首尾斜杠自动忽略",
    )

    permission_bits = models.IntegerField(
        default=1,
        verbose_name="权限位",
        help_text="READ=1 WRITE=2 CREATE=4 DELETE=8 SHARE=16，组合相加",
    )

    is_group_folder = models.BooleanField(
        default=True,
        verbose_name="是否 Group Folder",
        help_text="True=通过 Group Folders 插件管理；False=OCS 普通共享",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否生效",
    )

    class Meta:
        verbose_name = "NC 文件访问规则"
        verbose_name_plural = "NC 文件访问规则"
        unique_together = ("nc_group", "nc_path")
        ordering = ("nc_group_id", "nc_path")

    def __str__(self) -> str:
        return f"{self.nc_group.code} → {self.nc_path} [{self.permission_bits}]"
