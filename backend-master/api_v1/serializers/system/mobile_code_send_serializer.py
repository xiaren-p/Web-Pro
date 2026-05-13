"""发送手机验证码序列化器。"""
from rest_framework import serializers
from api_v1.serializers.system._mobile_regex import MOBILE_REGEX


class MobileCodeSendSerializer(serializers.Serializer):
    """请求发送手机短信验证码的入参序列化器。"""

    mobile = serializers.CharField(max_length=20)

    def validate_mobile(self, value: str) -> str:
        if not MOBILE_REGEX.match(value):
            raise serializers.ValidationError("手机号格式不正确")
        return value
