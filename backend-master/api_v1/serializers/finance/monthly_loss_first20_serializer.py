"""月度前 20 天亏损订单序列化器。"""
from api_v1.models import MonthlyLossOrderFirst20
from api_v1.serializers.finance.monthly_loss_serializer import MonthlyLossSerializer


class MonthlyLossFirst20Serializer(MonthlyLossSerializer):
    """字段与 :class:`MonthlyLossSerializer` 完全相同，只映射到 ``MonthlyLossOrderFirst20`` 模型。"""

    class Meta:
        model = MonthlyLossOrderFirst20
        fields = MonthlyLossSerializer.Meta.fields
