"""图片上传记录序列化器。"""
from rest_framework import serializers
from api_v1.models import ImageUpload


class ImageUploadSerializer(serializers.ModelSerializer):
    """图片上传记录序列化器（前端 camelCase 字段适配）。"""

    imageGroup = serializers.CharField(source="image_group")
    # cloudPath 允许缺省或留空（前端可能不带）
    cloudPath = serializers.CharField(source="cloud_path", required=False, allow_blank=True)
    imageUrl = serializers.CharField(source="image_url", required=False, allow_blank=True)
    createTime = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = ImageUpload
        fields = ["id", "imageGroup", "cloudPath", "status", "log", "imageUrl", "createTime"]
