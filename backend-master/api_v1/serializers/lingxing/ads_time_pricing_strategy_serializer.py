"""分时调价策略序列化器（LxTimePricingStrategy）。"""
from rest_framework import serializers
from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy


class LxTimePricingStrategySerializer(serializers.ModelSerializer):
    """分时调价策略全字段序列化器。

    创建时自动从 request.user 获取创建人用户名。
    """

    class Meta:
        model = LxTimePricingStrategy
        fields = "__all__"
        read_only_fields = ["id", "type", "created_at", "updated_at"]

    def create(self, validated_data):
        """创建时自动填充创建人。"""
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["creator"] = getattr(request.user, "username", "") or str(request.user)
        return super().create(validated_data)
