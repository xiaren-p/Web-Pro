"""刊登域 - URL 路由。

所有路径以 ``api/v1/sales/`` 为前缀（由 ``backend_master/urls.py`` 的 include 提供）。
"""
from django.urls import path

from apps.sales.publication.views.product_type_schema_view import (
    ProductTypeSchemaViewSet,
)
from apps.sales.publication.views.amazon_root_category_view import (
    AmazonRootCategoryViewSet,
)

urlpatterns: list[path] = [
    # ── 商品类型 Schema ──
    path(
        "product-type-schema",
        ProductTypeSchemaViewSet.as_view({"get": "get_product_type"}),
        name="product-type-schema",
    ),
    # ── Amazon 分类 ──
    path(
        "root-categories",
        AmazonRootCategoryViewSet.as_view({"get": "root_categories"}),
        name="root-categories",
    ),
    path(
        "category-children",
        AmazonRootCategoryViewSet.as_view({"get": "category_children"}),
        name="category-children",
    ),
    path(
        "category-search",
        AmazonRootCategoryViewSet.as_view({"get": "category_search"}),
        name="category-search",
    ),
]
