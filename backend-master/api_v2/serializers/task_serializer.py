"""工作流任务序列化器（task_serializer）。"""

from rest_framework import serializers

from api_v2.models.workflow_execution import WorkflowExecution, WorkflowType


class WorkflowStartSerializer(serializers.Serializer):
    """
    启动工作流请求参数序列化器。

    校验前端传入的工作流类型与执行参数，参数通过 params 字段透传给 Celery Task。
    """

    workflow_type = serializers.ChoiceField(
        choices=WorkflowType.choices,
        help_text='工作流类型',
    )

    params = serializers.JSONField(
        default=dict,
        help_text='工作流执行参数（随工作流类型不同而不同）',
    )


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """工作流执行记录响应序列化器。"""

    class Meta:
        model = WorkflowExecution
        fields = [
            'id',
            'workflow_type',
            'task_id',
            'status',
            'params',
            'result',
            'error_msg',
            'created_at',
            'started_at',
            'completed_at',
        ]
        read_only_fields = fields
