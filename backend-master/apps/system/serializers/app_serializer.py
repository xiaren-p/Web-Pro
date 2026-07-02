"""开发者应用管理序列化器（app_serializer）。"""

from oauth2_provider.models import get_application_model
from rest_framework import serializers

Application = get_application_model()


class AppCreateSerializer(serializers.Serializer):
    """
    创建开发者应用请求序列化器。

    前端仅需传入应用名称，client_id 与 client_secret 由后端自动生成，
    不允许外部传入以确保唯一性与随机强度。
    """

    name = serializers.CharField(
        max_length=100,
        help_text='应用名称（不超过 100 个字符）',
    )


class AppListItemSerializer(serializers.ModelSerializer):
    """
    应用列表单项响应序列化器。

    不包含 client_secret，保证密钥不被批量泄露；
    仅公开 client_id 供调用方识别应用身份。
    """

    class Meta:
        model = Application
        fields = ['id', 'name', 'client_id', 'created', 'updated']
        read_only_fields = fields


class AppCreatedSerializer(serializers.ModelSerializer):
    """
    应用创建成功响应序列化器。

    含 client_secret —— 此字段仅在创建时返回一次，后续接口不再提供。
    前端必须在收到响应后立即引导用户妥善保存，不得二次缓存至服务器。
    """

    class Meta:
        model = Application
        fields = ['id', 'name', 'client_id', 'client_secret', 'created']
        read_only_fields = fields


class SecretRotatedSerializer(serializers.Serializer):
    """
    密钥轮换成功响应序列化器。

    新 client_secret 仅此一次展示，同时返回轮换时间戳供审计。
    调用方应立即更新本地存储的 Secret 并作废旧 Secret 相关凭据。
    """

    client_secret = serializers.CharField(
        read_only=True,
        help_text='新的 Client Secret（仅此一次显示）',
    )

    rotated_at = serializers.DateTimeField(
        read_only=True,
        help_text='密钥轮换时间（UTC）',
    )
