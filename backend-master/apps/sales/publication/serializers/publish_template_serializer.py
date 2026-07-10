"""刊登模板序列化器。

列表序列化器不含 data_json（大字段），详情序列化器含 data_json。
写入序列化器接收 amazon_data，映射到 data_json。
"""
from rest_framework import serializers

from apps.sales.publication.models.publish_template import PublishTemplate


class PublishTemplateListSerializer(serializers.ModelSerializer):
    """模板列表序列化器（不含 data_json）。"""

    createUserName = serializers.CharField(source="create_user.username", read_only=True, default="")
    updateUserName = serializers.CharField(source="update_user.username", read_only=True, default="")

    class Meta:
        model = PublishTemplate
        fields = [
            "id",
            "template_name",
            "marketplace_id",
            "product_type",
            "product_type_unique_id",
            "country_code",
            "createUserName",
            "updateUserName",
            "created_at",
            "updated_at",
        ]


class PublishTemplateDetailSerializer(serializers.ModelSerializer):
    """模板详情序列化器（含 data_json）。"""

    createUserName = serializers.CharField(source="create_user.username", read_only=True, default="")
    updateUserName = serializers.CharField(source="update_user.username", read_only=True, default="")
    dataJson = serializers.JSONField(source="data_json", read_only=True)

    class Meta:
        model = PublishTemplate
        fields = [
            "id",
            "template_name",
            "marketplace_id",
            "product_type",
            "product_type_unique_id",
            "country_code",
            "dataJson",
            "createUserName",
            "updateUserName",
            "created_at",
            "updated_at",
        ]


class PublishTemplateWriteSerializer(serializers.Serializer):
    """模板写入序列化器（新增 / 编辑）。

    前端发送 amazon_data，后端映射到 data_json。
    """

    templateName = serializers.CharField(max_length=50)
    marketplaceId = serializers.CharField(max_length=64)
    productType = serializers.CharField(max_length=255)
    productTypeUniqueId = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    countryCode = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")
    amazonData = serializers.JSONField(required=False, default=dict)

    def create(self, validated_data: dict) -> PublishTemplate:
        """创建模板，amazon_data 映射到 data_json。"""
        user = self.context.get("request").user if self.context.get("request") else None
        return PublishTemplate.objects.create(
            template_name=validated_data["templateName"],
            marketplace_id=validated_data["marketplaceId"],
            product_type=validated_data["productType"],
            product_type_unique_id=validated_data.get("productTypeUniqueId", ""),
            country_code=validated_data.get("countryCode", ""),
            data_json=validated_data.get("amazonData", {}),
            create_user=user,
            update_user=user,
        )

    def update(self, instance: PublishTemplate, validated_data: dict) -> PublishTemplate:
        """更新模板，amazon_data 映射到 data_json。"""
        instance.template_name = validated_data.get("templateName", instance.template_name)
        instance.marketplace_id = validated_data.get("marketplaceId", instance.marketplace_id)
        instance.product_type = validated_data.get("productType", instance.product_type)
        instance.product_type_unique_id = validated_data.get("productTypeUniqueId", instance.product_type_unique_id)
        instance.country_code = validated_data.get("countryCode", instance.country_code)
        if "amazonData" in validated_data:
            instance.data_json = validated_data["amazonData"]
        user = self.context.get("request").user if self.context.get("request") else None
        if user:
            instance.update_user = user
        instance.save()
        return instance
