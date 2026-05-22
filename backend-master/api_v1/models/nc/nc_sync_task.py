"""Nextcloud 同步任务队列模型（nc_sync_task）。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class SyncOperation(models.TextChoices):
    """NC 同步操作类型枚举。"""

    CREATE_USER = "create_user", "创建 NC 用户"
    UPDATE_USER = "update_user", "更新 NC 用户"
    DISABLE_USER = "disable_user", "禁用 NC 用户"
    ENABLE_USER = "enable_user", "启用 NC 用户"
    ADD_TO_GROUP = "add_to_group", "加入 NC 群组"
    REMOVE_FROM_GROUP = "remove_from_group", "移出 NC 群组"
    CREATE_GROUP = "create_group", "创建 NC 群组"
    DELETE_GROUP = "delete_group", "删除 NC 群组"
    SET_ADMIN = "set_admin", "设置 NC 管理员"
    REVOKE_ADMIN = "revoke_admin", "撤销 NC 管理员"
    CREATE_GROUP_FOLDER = "create_group_folder", "创建 Group Folder"
    GRANT_GROUP_FOLDER = "grant_group_folder", "Group Folder 授权群组"


class SyncStatus(models.TextChoices):
    """NC 同步任务状态枚举。"""

    PENDING = "pending", "待执行"
    PROCESSING = "processing", "执行中"
    SUCCESS = "success", "已成功"
    FAILED = "failed", "已失败"


class NcSyncTask(TimeStampedModel):
    """NC 同步任务队列：记录所有待推送或失败待重试的同步操作。

    失败任务最多重试 MAX_RETRIES 次；超出后状态保持 FAILED，由运维手动处理或对账命令修复。
    """

    MAX_RETRIES: int = 3

    operation = models.CharField(
        max_length=30,
        choices=SyncOperation.choices,
        verbose_name="操作类型",
    )

    payload = models.JSONField(
        default=dict,
        verbose_name="操作参数",
        help_text="如 {\"username\": \"zhangsan\", \"group\": \"dept_tech\"}",
    )

    status = models.CharField(
        max_length=15,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        verbose_name="任务状态",
        db_index=True,
    )

    error_msg = models.TextField(
        blank=True,
        default="",
        verbose_name="错误信息",
    )

    retry_count = models.IntegerField(
        default=0,
        verbose_name="已重试次数",
    )

    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="最后执行时间",
    )

    class Meta:
        verbose_name = "NC 同步任务"
        verbose_name_plural = "NC 同步任务"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "retry_count"], name="idx_nc_sync_status_retry"),
        ]

    def __str__(self) -> str:
        return f"NcSyncTask<{self.operation}>[{self.status}]"
