"""绑定邮箱序列化器。"""
from rest_framework import serializers


class EmailBindSerializer(serializers.Serializer):
    """绑定邮箱入参（邮箱 + 验证码）。"""

    email = serializers.EmailField()
    code = serializers.CharField(max_length=10)
