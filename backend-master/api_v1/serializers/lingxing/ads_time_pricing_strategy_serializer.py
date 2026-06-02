"""分时调价策略序列化器（LxTimePricingStrategy）。"""
from rest_framework import serializers
from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy


class LxTimePricingStrategySerializer(serializers.ModelSerializer):
    """分时调价策略全字段序列化器。"""

    class Meta:
        model = LxTimePricingStrategy
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
