"""刊登域 - URL 路由。

所有路径以 ``api/v1/sales/`` 为前缀（由 ``backend_master/urls.py`` 的 include 提供）。
"""
from django.urls import path

from apps.sales.publication.views.product_type_schema_view import (
    ProductTypeSchemaViewSet,
)

urlpatterns: list[path] = [
    path(
        "product-type-schema",
        ProductTypeSchemaViewSet.as_view({"get": "get_product_type"}),
        name="product-type-schema",
    ),
]
