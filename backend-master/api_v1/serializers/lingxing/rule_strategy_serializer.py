"""广告规则策略序列化器（LxAdRule / LxAdRuleGroup）。"""
import re

from rest_framework import serializers

from api_v1.models.lingxing.ads.lx_ad_rule import LxAdRule
from api_v1.models.lingxing.ads.lx_ad_rule_group import LxAdRuleGroup


def _snake_to_camel(name: str) -> str:
    """将 snake_case 转为 lowerCamelCase。

    Args:
        name: snake_case 字符串

    Returns:
        lowerCamelCase 字符串
    """
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _camel_to_snake(name: str) -> str:
    """将 lowerCamelCase 转为 snake_case。

    Args:
        name: lowerCamelCase 字符串

    Returns:
        snake_case 字符串
    """
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def _to_camel_case(data: dict) -> dict:
    """将 dict 的所有 key 从 snake_case 转为 camelCase。"""
    return {_snake_to_camel(k): v for k, v in data.items()}


class LxAdRuleSerializer(serializers.ModelSerializer):
    """广告规则序列化器。

    对外输出 lowerCamelCase 键名，与前端 RuleFormData 接口对齐。
    创建时自动从 request.user 获取创建人用户名。
    """

    class Meta:
        model = LxAdRule
        fields = "__all__"
        read_only_fields = ["id", "creator", "created_at", "updated_at"]

    def to_representation(self, instance):
        """将输出键名转为 camelCase。"""
        data = super().to_representation(instance)
        # 修复 DecimalField 序列化问题：Decimal → float
        for key in ("add_keyword_max_bid", "add_keyword_fixed_bid"):
            if data.get(key) is not None:
                data[key] = float(data[key])
        return _to_camel_case(data)

    def to_internal_value(self, data):
        """将前端 camelCase 键名转回 snake_case。"""
        snake_data = {_camel_to_snake(k): v for k, v in data.items()}
        return super().to_internal_value(snake_data)

    def create(self, validated_data):
        """创建时自动填充创建人。"""
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["creator"] = getattr(request.user, "username", "") or str(request.user)
        return super().create(validated_data)


class LxAdRuleGroupSerializer(serializers.ModelSerializer):
    """规则组序列化器。

    输出时将 rule_order（ID 数组）展开为 rules（完整规则对象数组）。
    """

    rules = serializers.SerializerMethodField(read_only=True, help_text="展开后的完整规则列表")

    class Meta:
        model = LxAdRuleGroup
        fields = ["id", "name", "execution_cycle", "rule_order", "rules", "creator", "created_at", "updated_at"]
        read_only_fields = ["id", "creator", "created_at", "updated_at"]

    def get_rules(self, obj) -> list[dict]:
        """根据 rule_order 批量加载规则并序列化。"""
        if not obj.rule_order:
            return []
        # 保持 rule_order 的顺序加载规则
        rule_ids = obj.rule_order
        rules_map = {
            r.id: r for r in LxAdRule.objects.filter(id__in=rule_ids)
        }
        ordered = [rules_map.get(rid) for rid in rule_ids]
        return [LxAdRuleSerializer(rule).data for rule in ordered if rule is not None]

    def to_representation(self, instance):
        """将输出键名转为 camelCase。"""
        data = super().to_representation(instance)
        return _to_camel_case(data)

    def to_internal_value(self, data):
        """将前端 camelCase 键名转回 snake_case。"""
        snake_data = {_camel_to_snake(k): v for k, v in data.items()}
        # 前端可能传 rules 数组，但后端只存 rule_order ID 数组
        if "rules" in snake_data:
            del snake_data["rules"]
        return super().to_internal_value(snake_data)

    def create(self, validated_data):
        """创建时自动填充创建人。"""
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["creator"] = getattr(request.user, "username", "") or str(request.user)
        return super().create(validated_data)
