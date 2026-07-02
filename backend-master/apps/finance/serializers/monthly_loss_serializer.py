"""月度亏损订单序列化器。"""
from rest_framework import serializers
from apps.finance.models.monthly_loss_order import MonthlyLossOrder


class MonthlyLossSerializer(serializers.ModelSerializer):
    """月度亏损订单序列化器：仅以英文字段名作为输入与输出。"""

    # 后端定型百分比字段，前端直接渲染，无需 formatPercent
    gross_margin_display = serializers.SerializerMethodField()
    net_gross_margin_display = serializers.SerializerMethodField()
    return_rate_display = serializers.SerializerMethodField()
    refund_amount_rate_display = serializers.SerializerMethodField()
    spend_rate_display = serializers.SerializerMethodField()

    @staticmethod
    def _fmt_percent(v) -> str:
        """统一百分比格式化：小数 → ``"xx.xx%"``，``None`` 返回空串。"""
        if v is None or v == "":
            return ""
        try:
            return f"{round(float(v) * 100, 2)}%"
        except (TypeError, ValueError):
            return ""

    def get_gross_margin_display(self, obj) -> str:
        """获取 gross_margin_display。"""
        return self._fmt_percent(obj.gross_margin)

    def get_net_gross_margin_display(self, obj) -> str:
        """获取 net_gross_margin_display。"""
        return self._fmt_percent(obj.net_gross_margin)

    def get_return_rate_display(self, obj) -> str:
        """获取 return_rate_display。"""
        return self._fmt_percent(obj.return_rate)

    def get_refund_amount_rate_display(self, obj) -> str:
        """获取 refund_amount_rate_display。"""
        return self._fmt_percent(obj.refund_amount_rate)

    def get_spend_rate_display(self, obj) -> str:
        """获取 spend_rate_display。"""
        return self._fmt_percent(obj.spend_rate)

    def to_internal_value(self, data):
        # 入参 JSON key 必须是英文字段名（不再做中文兼容）
        """反序列化入参为内部值。

强制要求英文字段名，不再兼容中文 key。

Args:
    data: 原始输入数据。

Returns:
    dict: 反序列化后的内部值。
"""
        if not isinstance(data, dict):
            return super().to_internal_value(data)
        return super().to_internal_value(data)

    def to_representation(self, instance):
        """序列化实例为前端输出结构。

输出英文字段名，并补全元数据字段。

Args:
    instance: MonthlyLossOrder 模型实例。

Returns:
    dict: 序列化后的输出字典。
"""
        rep = super().to_representation(instance)
        # 输出英文字段名
        out = {}
        for en, val in rep.items():
            out[en] = val
        # 兼容标准元数据字段（id / created_at / updated_at）
        if "created_at" in rep:
            out["created_at"] = rep.get("created_at")
        if "updated_at" in rep:
            out["updated_at"] = rep.get("updated_at")
        if "id" in rep:
            out["id"] = rep.get("id")
        return out

    class Meta:
        model = MonthlyLossOrder
        fields = [
            "id", "image_url", "msku", "asin", "parent_asin", "store_country",
            "product_name_sku", "gross_profit", "gross_margin", "gross_margin_display",
            "net_gross_margin", "net_gross_margin_display",
            "return_rate", "return_rate_display",
            "refund_amount_rate", "refund_amount_rate_display",
            "total_stock_fee", "spend",
            "spend_rate", "spend_rate_display",
            "sales", "owner", "month", "created_at", "updated_at",
        ]
