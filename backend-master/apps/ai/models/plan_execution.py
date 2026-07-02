"""AI Plan 执行审计表（ai_plan_execution）。"""

from django.contrib.auth.models import User
from django.db import models

from apps.ai.models.message import AiMessage


class PlanExecutionStatus(models.TextChoices):
    """Plan 执行状态枚举。"""

    PENDING = 'pending', '待执行'
    SUCCESS = 'success', '已执行'
    FAILED = 'failed', '失败'
    CANCELLED = 'cancelled', '已取消'


class AiPlanExecution(models.Model):
    """AI Plan 提案执行审计记录。

    职责：
        当用户对 AI 返回的 Plan 卡片点击"确认"按钮时，落一条本表记录用于合规留痕，
        即便业务执行端点（如采购单创建）尚未接入也保留该记录便于后续回查。
        ``payload`` 存用户在卡片上勾选 / 填写的最终结构，``result`` 存业务端点执行结果。
        本期版本下，业务端点未接入时 ``status`` 保持 PENDING 即可，前端只会本地提示。
    """

    message = models.OneToOneField(
        AiMessage,
        on_delete=models.CASCADE,
        related_name='plan_execution',
        verbose_name='源消息',
    )

    plan_id = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name='Plan ID',
    )

    endpoint = models.CharField(
        max_length=200,
        verbose_name='调用端点',
    )

    payload = models.JSONField(
        verbose_name='请求载荷',
    )

    status = models.CharField(
        max_length=16,
        choices=PlanExecutionStatus.choices,
        default=PlanExecutionStatus.PENDING,
        db_index=True,
        verbose_name='执行状态',
    )

    result = models.JSONField(
        null=True,
        blank=True,
        verbose_name='执行结果',
    )

    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_plan_executions',
        verbose_name='执行人',
    )

    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='执行时间',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )

    class Meta:
        managed = True
        db_table = 'ai_plan_execution'
        verbose_name = 'AI Plan 执行审计'
        verbose_name_plural = 'AI Plan 执行审计'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"AiPlanExecution<{self.pk} {self.plan_id} {self.status}>"
