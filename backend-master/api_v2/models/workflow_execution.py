"""工作流执行记录表（workflow_execution）。"""

from django.contrib.auth.models import User
from django.db import models


class WorkflowType(models.TextChoices):
    """工作流类型枚举。"""

    LISTING_IMAGE_UPLOAD = 'listing_image_upload', 'Listing 图片上传'


class ExecutionStatus(models.TextChoices):
    """任务执行状态枚举。"""

    PENDING = 'pending', '待执行'
    RUNNING = 'running', '执行中'
    COMPLETED = 'completed', '已完成'
    FAILED = 'failed', '失败'
    CANCELLED = 'cancelled', '已取消'


class WorkflowExecution(models.Model):
    """工作流执行记录（任务生命周期的核心追踪表）。"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workflow_executions',
        verbose_name='触发用户',
    )

    workflow_type = models.CharField(
        max_length=50,
        choices=WorkflowType.choices,
        db_index=True,
        verbose_name='工作流类型',
    )

    task_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Celery Task ID',
    )

    status = models.CharField(
        max_length=20,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.PENDING,
        db_index=True,
        verbose_name='执行状态',
    )

    params = models.JSONField(
        default=dict,
        verbose_name='执行参数',
    )

    result = models.JSONField(
        null=True,
        blank=True,
        verbose_name='执行结果',
    )

    error_msg = models.TextField(
        blank=True,
        verbose_name='错误信息',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='开始时间',
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间',
    )

    class Meta:
        managed = True
        db_table = 'workflow_execution'
        verbose_name = '工作流执行记录'
        verbose_name_plural = '工作流执行记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow_type', 'status']),
            models.Index(fields=['user_id', 'created_at']),
        ]

    def __str__(self) -> str:
        return f"WorkflowExecution<{self.pk}>"
