"""绑定手机号序列化器。"""
from rest_framework import serializers
from api_v1.serializers.system._mobile_regex import MOBILE_REGEX


class MobileBindSerializer(serializers.Serializer):
    """绑定手机号入参（手机号 + 短信验证码）。"""

    mobile = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=10)

    def validate_mobile(self, value: str) -> str:
        if not MOBILE_REGEX.match(value):
            raise serializers.ValidationError("手机号格式不正确")
        return value
