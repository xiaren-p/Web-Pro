"""发送邮箱验证码序列化器。"""
from rest_framework import serializers


class EmailCodeSendSerializer(serializers.Serializer):
    """请求发送邮箱验证码的入参序列化器。"""

    email = serializers.EmailField()
