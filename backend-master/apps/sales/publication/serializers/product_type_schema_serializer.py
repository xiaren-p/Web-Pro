"""Amazon 商品类型 Schema 序列化器。

后端预处理 properties / properties_zh（JSON 文本），提取 required、$defs、
字段定义、字段分组等核心结构，以 camelCase 直接输出，前端无需二次 JSON.parse。

propertyGroups / propertyGroupsZh 基于硬编码的 FIELD_GROUP_MAP 动态构建，
根据当前 schema 实际存在的字段名匹配分组。
"""
import json
import logging

from rest_framework import serializers

from apps.sales.publication.models.amazon_product_type_schema import AmazonProductTypeSchema

logger = logging.getLogger(__name__)

# ── 字段名 → 分组映射（亚马逊 7 组标准分类，固定不变）─────────────────────

# 每组的中文 / 站点语言标题
_GROUP_INFO: dict[str, dict[str, str]] = {
    "offer":                   {"zh": "报价",         "en": "Offer"},
    "images":                  {"zh": "图片",         "en": "Images"},
    "shipping":                {"zh": "运输",         "en": "Shipping"},
    "variations":              {"zh": "变种",         "en": "Variations"},
    "safety_and_compliance":   {"zh": "安全与合规",   "en": "Safety and Compliance"},
    "product_identity":        {"zh": "产品识别",     "en": "Product Identity"},
    "product_details":         {"zh": "产品详情",     "en": "Product Details"},
}

# 字段归属规则：后写的优先级高于先写（同一个字段出现在多个组时以后面为准）
# 未匹配的字段兜底归 product_details
_FIELD_GROUP_RULES: dict[str, list[str]] = {
    "shipping": [
        "item_dimensions",
        "item_package_dimensions",
        "item_package_weight",
        "epr_product_packaging",
        "master_pack_layers_per_pallet_quantity",
        "master_packs_per_layer_quantity",
    ],
    "offer": [
        "skip_offer",
        "fulfillment_availability",
        "purchasable_offer",
        "condition_type",
        "condition_note",
        "list_price",
        "product_tax_code",
        "merchant_release_date",
        "merchant_shipping_group",
        "max_order_quantity",
        "gift_options",
        "uvp_list_price",
        "main_offer_image_locator",
        "other_offer_image_locator_1",
        "other_offer_image_locator_2",
        "other_offer_image_locator_3",
        "other_offer_image_locator_4",
        "other_offer_image_locator_5",
        "supplemental_condition_information",
    ],
    "images": [
        "main_product_image_locator",
        "other_product_image_locator_1",
        "other_product_image_locator_2",
        "other_product_image_locator_3",
        "other_product_image_locator_4",
        "other_product_image_locator_5",
        "other_product_image_locator_6",
        "other_product_image_locator_7",
        "other_product_image_locator_8",
        "swatch_product_image_locator",
        "image_locator_ps01",
        "image_locator_ps02",
        "image_locator_ps03",
        "image_locator_ps04",
        "image_locator_ps05",
        "image_locator_ps06",
    ],
    "variations": [
        "parentage_level",
        "child_parent_sku_relationship",
        "variation_theme",
    ],
    "safety_and_compliance": [
        "country_of_origin",
        "batteries_required",
        "batteries_included",
        "battery",
        "num_batteries",
        "number_of_lithium_metal_cells",
        "number_of_lithium_ion_cells",
        "lithium_battery",
        "supplier_declared_dg_hz_regulation",
        "hazmat",
        "safety_data_sheet_url",
        "is_this_product_subject_to_buyer_age_restrictions",
        "regulatory_compliance_certification",
        "dsa_responsible_party_address",
        "compliance_media",
        "gpsr_safety_attestation",
        "gpsr_manufacturer_reference",
        "ships_globally",
        "has_less_than_30_percent_state_of_charge",
        "epr_eco_fee_eubr",
        "supplier_declared_dg_hz_regulation_chemicals",
        "supplier_declared_dg_hz_regulation_ghs",
        "is_discontinued_by_manufacturer",
        "ghs",
        "ghs_chemical_h_code",
        "supplier_declared_dg_hz_regulation",
    ],
    "product_identity": [
        "item_name",
        "title_differentiation",
        "brand",
        "supplier_declared_has_product_identifier_exemption",
        "externally_assigned_product_identifier",
        "merchant_suggested_asin",
        "recommended_browse_nodes",
        "model_number",
        "model_name",
        "manufacturer",
        "catalog_number",
        "item_type_keyword",
        "item_type_name",
    ],
    "product_details": [
        "product_description",
        "bullet_point",
        "generic_keyword",
        "style",
        "material",
        "number_of_items",
        "item_package_quantity",
        "color",
        "size",
        "part_number",
        "subject_keyword",
        "edition",
        "format",
        "configuration",
        "hardware_platform",
        "computer_platform",
        "platform_for_display",
        "processor_description",
        "language",
        "content_type",
        "publication_date",
        "genre",
        "access_method",
        "operating_system",
        "customer_package_type",
        "pattern",
        "product_site_launch_date",
        "hard_disk",
        "software_requirement",
        "subscription_term",
        "number_of_licenses",
        "supported_devices_quantity",
        "is_green_purchasing_law_compliant",
        "item_weight",
        "fabric_type",
        "weave_type",
        "neck_size",
        "sleeve_length",
        "shirt_size",
        "fit_type",
        "collar_style",
        "outer",
        "water_resistance_level",
        "sport_type",
        "team_name",
        "league_name",
        "hand_orientation",
        "compatible_devices",
        "included_components",
        "warranty_description",
        "backing",
        "grip",
        "grit",
        "item_thickness",
        "item_length_width",
        "hardness",
        "number_of_packs",
        "set_name",
        "collection_item",
        "unit_count",
        "item_diameter",
        "package_contains_sku",
        "package_level",
    ],
}

# 构建最终映射：遍历所有规则，同一个字段出现在多个组时以后面为准
_FIELD_TO_GROUP: dict[str, str] = {}
for _group_key, _field_names in _FIELD_GROUP_RULES.items():
    for _name in _field_names:
        _FIELD_TO_GROUP[_name] = _group_key


def _build_property_groups(schema_properties: dict, lang: str) -> dict:
    """根据 schema 实际存在的字段，动态构建属性分组。

    Args:
        schema_properties: ``properties.properties``（字段名 → 字段定义）。
        lang: ``"zh"`` 或 ``"en"``，决定 title 语言。

    Returns:
        ``{ group_key: { title, propertyNames } }``，不含空组。
    """
    groups: dict[str, dict] = {}
    schema_field_names = set(schema_properties.keys())

    for field_name in schema_field_names:
        group_key = _FIELD_TO_GROUP.get(field_name, "product_details")
        if group_key not in groups:
            groups[group_key] = {
                "title": _GROUP_INFO[group_key].get(lang, group_key),
                "propertyNames": [],
            }
        groups[group_key]["propertyNames"].append(field_name)

    return groups


# variation_theme 枚举分量后缀（如 STYLE_NAME → style）
_VT_SUFFIXES = ["_name", "_type", "_quantity", "_count"]


def _theme_part_to_field(part: str) -> str | None:
    """将 variation_theme 枚举分量转为 schema 字段名。"""
    word = part.strip().lower()
    for suffix in _VT_SUFFIXES:
        if word.endswith(suffix):
            word = word[:-len(suffix)]
            break
    return word or None


class ProductTypeSchemaSerializer(serializers.Serializer):
    """商品类型 Schema 读取序列化器。

    将 model 中的 properties / properties_zh（JSON 文本）解析后拆分为
    fields / fieldsZh / requiredFields / defaultFields / propertyGroups，
    前端可直接消费。

    性能优化：to_representation 中预解析 properties 和 properties_zh
    各一次，避免多个 get_* 方法各自重复解析大 JSON。
    """

    productTypeUniqueId = serializers.CharField(source="product_type_unique_id", read_only=True)
    marketplaceId = serializers.CharField(source="marketplace_id", read_only=True)
    productTypeOrigin = serializers.CharField(source="product_type_origin", read_only=True)
    displayName = serializers.CharField(source="display_name", read_only=True)
    requiredFields = serializers.SerializerMethodField()
    defaultFields = serializers.SerializerMethodField()
    fields = serializers.SerializerMethodField(method_name="get_schema_fields")
    fieldsZh = serializers.SerializerMethodField(method_name="get_schema_fields_zh")
    propertyGroups = serializers.SerializerMethodField(method_name="get_property_groups")
    propertyGroupsZh = serializers.SerializerMethodField(method_name="get_property_groups_zh")

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
        """提取全部必填字段名列表。

        来源：
        1. 根级 required 数组（始终 6 个）
        2. allOf 块中的 required（DB 有则取）
        3. variation_theme 枚举值反推字段引用
        """
        props = self._parsed_props
        result: list[str] = list(props.get("required", []))

        # 扫描 allOf 块
        def _scan_all_of(blocks: list) -> None:
            if not isinstance(blocks, list):
                return
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if "required" in block and isinstance(block["required"], list):
                    result.extend(block["required"])
                if "then" in block and isinstance(block["then"], dict):
                    _scan_all_of([block["then"]])
                if "else" in block and isinstance(block["else"], dict):
                    _scan_all_of([block["else"]])

        _scan_all_of(props.get("allOf", []))

        # variation_theme 推导
        field_defs = props.get("properties", {})
        vt = field_defs.get("variation_theme", {})
        vt_names = (
            vt.get("items", {})
            .get("properties", {})
            .get("name", {})
            .get("enum", [])
        )
        for name in vt_names:
            if not isinstance(name, str):
                continue
            for part in name.split("/"):
                key = _theme_part_to_field(part.strip())
                if key and key in field_defs:
                    result.append(key)

        return list(dict.fromkeys(result))  # 去重保序

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

    def get_property_groups(self, obj: AmazonProductTypeSchema) -> dict:
        """构建站点语言版本的属性分组。"""
        return _build_property_groups(self._parsed_props.get("properties", {}), "en")

    def get_property_groups_zh(self, obj: AmazonProductTypeSchema) -> dict:
        """构建中文版本的属性分组。"""
        return _build_property_groups(self._parsed_props_zh.get("properties", {}), "zh")
