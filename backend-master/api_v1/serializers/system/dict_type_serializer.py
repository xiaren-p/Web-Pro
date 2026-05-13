"""字典类型序列化器。"""
from rest_framework import serializers
from api_v1.models import DictType


class DictTypeSerializer(serializers.ModelSerializer):
    """字典类型读写序列化器。"""

    dictCode = serializers.CharField(source="code")
    status_text = serializers.SerializerMethodField()

    def get_status_text(self, obj) -> str:
        """字典类型状态中文标签，前端直接展示。"""
        return "启用" if obj.status else "禁用"

    class Meta:
        model = DictType
        fields = ["id", "name", "dictCode", "status", "status_text"]
