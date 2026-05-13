"""系统配置序列化器。"""
from rest_framework import serializers
from api_v1.models import Config


class ConfigSerializer(serializers.ModelSerializer):
    """系统配置读写序列化器。"""

    configName = serializers.CharField(source="key")
    configKey = serializers.CharField(source="key")
    configValue = serializers.CharField(source="value")

    class Meta:
        model = Config
        fields = ["id", "configName", "configKey", "configValue", "status", "remark"]
