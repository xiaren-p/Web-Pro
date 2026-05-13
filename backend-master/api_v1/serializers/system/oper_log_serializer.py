"""操作日志序列化器。"""
from rest_framework import serializers
from api_v1.models import OperLog


class OperLogSerializer(serializers.ModelSerializer):
    """系统操作日志只读序列化器。"""

    class Meta:
        model = OperLog
        fields = [
            "id", "module", "action", "operator", "ip", "user_agent", "result", "elapsed_ms", "created_at",
        ]
