"""角色写入序列化器。"""
from rest_framework import serializers
from api_v1.models import Role


class RoleWriteSerializer(serializers.ModelSerializer):
    """角色写入序列化器（接收 1/0 数字状态、前后端字段别名映射）。"""

    sort = serializers.IntegerField(source="order_num", required=False)
    status = serializers.IntegerField(required=False)
    dataScope = serializers.IntegerField(source="data_scope", required=False)

    def validate_status(self, value):
        return bool(int(value))

    class Meta:
        model = Role
        fields = ["code", "name", "remark", "sort", "status", "dataScope"]
