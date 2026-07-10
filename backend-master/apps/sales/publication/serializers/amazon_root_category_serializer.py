"""Amazon 根分类序列化器。

camelCase 直接输出，数组字段走 JSONField 透传，字符串字段走 CharField。
"""
from rest_framework import serializers

from apps.sales.publication.models.amazon_root_category import AmazonRootCategory


class AmazonRootCategorySerializer(serializers.Serializer):
    """Amazon 分类节点序列化器（前端 camelCase 适配）。"""

    categoryUniqueId = serializers.CharField(source="category_unique_id", read_only=True)
    categoryName = serializers.CharField(source="category_name", read_only=True)
    categoryId = serializers.IntegerField(source="category_id", read_only=True)
    marketplaceId = serializers.CharField(source="marketplace_id", read_only=True)
    parentId = serializers.IntegerField(source="parent_id", read_only=True)
    isRoot = serializers.IntegerField(source="is_root", read_only=True)
    hasChildren = serializers.IntegerField(source="has_children", read_only=True)
    childCategories = serializers.JSONField(source="child_categories", read_only=True)
    productTypeOrigin = serializers.JSONField(source="product_type_origin", read_only=True)
    browseNodeAttributes = serializers.CharField(source="browse_node_attributes", read_only=True)
    categoryPathId = serializers.CharField(source="category_path_id", read_only=True)
    categoryPathName = serializers.CharField(source="category_path_name", read_only=True)
