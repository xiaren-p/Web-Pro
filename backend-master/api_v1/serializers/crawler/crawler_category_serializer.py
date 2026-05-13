"""爬虫分类序列化器。"""
from rest_framework import serializers
from api_v1.models import CrawlerCategory


class CrawlerCategorySerializer(serializers.ModelSerializer):
    """爬虫分类序列化器，前端字段与模型字段保持一致。"""

    status_text = serializers.SerializerMethodField()

    def get_status_text(self, obj) -> str:
        """爬虫分类状态中文标签，前端表格列直接展示。"""
        return "正常" if obj.status == 1 else "禁用"

    class Meta:
        model = CrawlerCategory
        fields = [
            "id", "name", "category_id", "site", "category_type",
            "status", "status_text", "created_at", "updated_at",
        ]
