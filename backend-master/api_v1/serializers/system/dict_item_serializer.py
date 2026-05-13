"""字典项序列化器。"""
from rest_framework import serializers
from api_v1.models import DictItem


class DictItemSerializer(serializers.ModelSerializer):
    """字典项读写序列化器（status 统一映射为 1/0 数字）。"""

    status = serializers.SerializerMethodField()
    status_text = serializers.SerializerMethodField()
    tagType = serializers.CharField(source="tag_type", required=False, allow_blank=True)

    def get_status(self, obj) -> int:
        return 1 if obj.status else 0

    def get_status_text(self, obj) -> str:
        """状态中文标签：前端表格直接展示，避免在视图层做枚举翻译。"""
        return "启用" if obj.status else "禁用"

    class Meta:
        model = DictItem
        fields = ["id", "label", "value", "sort", "status", "status_text", "tagType"]
