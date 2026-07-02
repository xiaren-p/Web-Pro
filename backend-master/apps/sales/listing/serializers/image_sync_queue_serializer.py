"""图片同步队列序列化器。

遵循"数据出口最终成形原则"：后端直接输出 camelCase 字段，
前端拿到即可渲染，不再做字段重映射。
"""
from rest_framework import serializers

from apps.sales.listing.models import ImageSyncQueue


class ImageSyncQueueSerializer(serializers.ModelSerializer):
    """图片同步队列序列化器（前端 camelCase 字段适配）。"""

    imageGroup = serializers.CharField(source="sku")
    cloudPath = serializers.CharField(source="local_path")
    errorMsg = serializers.CharField(source="error_msg", read_only=True)
    createTime = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = ImageSyncQueue
        fields = ["id", "imageGroup", "cloudPath", "status", "errorMsg", "createTime"]
