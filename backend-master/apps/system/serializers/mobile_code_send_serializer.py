"""发送手机验证码序列化器。"""
from rest_framework import serializers
from apps.system.serializers._mobile_regex import MOBILE_REGEX


class MobileCodeSendSerializer(serializers.Serializer):
    """请求发送手机短信验证码的入参序列化器。"""

    mobile = serializers.CharField(max_length=20)

    def validate_mobile(self, value: str) -> str:
        """校验手机号格式是否合法。

Args:
    value (str): 待校验手机号。

Returns:
    str: 校验通过的手机号。

Raises:
    serializers.ValidationError: 手机号格式不正确时抛出。
"""
        if not MOBILE_REGEX.match(value):
            raise serializers.ValidationError("手机号格式不正确")
        return value
