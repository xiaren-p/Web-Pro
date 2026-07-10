"""刊登域 - URL 路由。

所有路径以 ``api/v1/sales/`` 为前缀（由 ``backend_master/urls.py`` 的 include 提供）。
刊登域子路由统一加 ``publication/`` 前缀，突出刊登域归属。
"""
from django.urls import path

from apps.sales.publication.views.product_type_schema_view import (
    ProductTypeSchemaViewSet,
)
from apps.sales.publication.views.amazon_root_category_view import (
    AmazonRootCategoryViewSet,
)
from apps.sales.publication.views.publish_template_view import (
    PublishTemplateViewSet,
)
from apps.sales.publication.views.marketplace_view import (
    MarketplaceViewSet,
)

urlpatterns: list[path] = [
    # ── 商品类型 Schema ──
    path(
        "publication/product-type-schema",
        ProductTypeSchemaViewSet.as_view({"get": "get_product_type"}),
        name="product-type-schema",
    ),
    # ── Amazon 分类 ──
    path(
        "publication/root-categories",
        AmazonRootCategoryViewSet.as_view({"get": "root_categories"}),
        name="root-categories",
    ),
    path(
        "publication/category-children",
        AmazonRootCategoryViewSet.as_view({"get": "category_children"}),
        name="category-children",
    ),
    path(
        "publication/category-search",
        AmazonRootCategoryViewSet.as_view({"get": "category_search"}),
        name="category-search",
    ),
    # ── Amazon 市场列表 ──
    path(
        "publication/marketplaces",
        MarketplaceViewSet.as_view({"get": "list_marketplaces"}),
        name="publication-marketplaces",
    ),
    # ── 刊登模板 CRUD ──
    path(
        "publication/templates/page",
        PublishTemplateViewSet.as_view({"get": "page"}),
        name="publication-templates-page",
    ),
    path(
        "publication/templates",
        PublishTemplateViewSet.as_view({"post": "create_template"}),
        name="publication-templates-create",
    ),
    path(
        "publication/templates/<str:pk>/form",
        PublishTemplateViewSet.as_view({"get": "form"}),
        name="publication-templates-form",
    ),
    path(
        "publication/templates/<str:pk>",
        PublishTemplateViewSet.as_view({"put": "update_template", "delete": "delete_template"}),
        name="publication-templates-detail",
    ),
]
