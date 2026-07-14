"""Amazon 商品类型 Schema 序列化器。

后端预处理 properties / properties_zh（JSON 文本），提取 required、$defs、
字段定义等核心结构，以 camelCase 直接输出，前端无需二次 JSON.parse。
"""
import json
import logging

from rest_framework import serializers

from apps.sales.publication.models.amazon_product_type_schema import AmazonProductTypeSchema

logger = logging.getLogger(__name__)


class ProductTypeSchemaSerializer(serializers.Serializer):
    """商品类型 Schema 读取序列化器。

    将 model 中的 properties / properties_zh（JSON 文本）解析后拆分为
    fields / fieldsZh / requiredFields / defaultFields，前端可直接消费。

    性能优化：to_representation 中预解析 properties 和 properties_zh
    各一次，避免 4 个 get_* 方法各自重复解析大 JSON。
    """

    productTypeUniqueId = serializers.CharField(source="product_type_unique_id", read_only=True)
    marketplaceId = serializers.CharField(source="marketplace_id", read_only=True)
    productTypeOrigin = serializers.CharField(source="product_type_origin", read_only=True)
    displayName = serializers.CharField(source="display_name", read_only=True)
    requiredFields = serializers.SerializerMethodField()
    defaultFields = serializers.SerializerMethodField()
    fields = serializers.SerializerMethodField(method_name="get_schema_fields")
    fieldsZh = serializers.SerializerMethodField(method_name="get_schema_fields_zh")

    def to_representation(self, instance: AmazonProductTypeSchema) -> dict:
        """序列化入口：预解析 JSON，缓存到实例私有属性上。"""
        self._parsed_props = self._safe_parse(instance.properties)
        self._parsed_props_zh = self._safe_parse(instance.properties_zh)
        return super().to_representation(instance)

    @staticmethod
    def _safe_parse(raw: str) -> dict:
        """安全解析 JSON 文本，失败时返回空 dict。"""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("[ProductTypeSchemaSerializer] JSON 解析失败: %s", e)
            return {}

    def get_requiredFields(self, obj: AmazonProductTypeSchema) -> list:
        """从 properties 根级提取必填字段名列表。"""
        return self._parsed_props.get("required", [])

    def get_defaultFields(self, obj: AmazonProductTypeSchema) -> dict:
        """从 $defs 提取 marketplace_id / language_tag 默认值。"""
        defs = self._parsed_props.get("$defs", {})
        defaults: dict[str, str] = {}
        for key, val in defs.items():
            if isinstance(val, dict) and "default" in val:
                defaults[key] = val["default"]
        return defaults

    def get_schema_fields(self, obj: AmazonProductTypeSchema) -> dict:
        """提取站点语言版本的字段定义（properties.properties）。"""
        return self._parsed_props.get("properties", {})

    def get_schema_fields_zh(self, obj: AmazonProductTypeSchema) -> dict:
        """提取中文版本的字段定义（properties_zh.properties）。"""
        return self._parsed_props_zh.get("properties", {})
