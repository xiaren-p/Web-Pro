"""角色读取序列化器。"""
from rest_framework import serializers
from api_v1.models import Role


class RoleSerializer(serializers.ModelSerializer):
    """角色读取序列化器（前后端字段别名映射）。"""

    sort = serializers.IntegerField(source="order_num")
    status = serializers.SerializerMethodField()
    dataScope = serializers.IntegerField(source="data_scope")

    def get_status(self, obj):
        return 1 if obj.status else 0

    class Meta:
        model = Role
        fields = ["id", "code", "name", "status", "remark", "sort", "dataScope", "created_at", "updated_at"]
