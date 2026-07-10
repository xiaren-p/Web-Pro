"""Amazon 商品类型 Schema 视图。

提供 getProductType 接口，后端预处理 properties / properties_zh（JSON 文本），
拆分为 fields / fieldsZh / requiredFields / defaultFields 后返回，前端可直接消费。

路由前缀：api/v1/sales/（由 backend_master/urls.py 的 include 提供）
"""
import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.utils.responses import drf_error, drf_ok
from apps.sales.publication.selectors.product_type_schema_selector import (
    get_product_type_schema,
)
from apps.sales.publication.serializers.product_type_schema_serializer import (
    ProductTypeSchemaSerializer,
)

logger = logging.getLogger(__name__)


class ProductTypeSchemaViewSet(viewsets.ViewSet):
    """Amazon 商品类型 Schema 接口。

    路由前缀：/sales/product-type-schema
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="")
    def get_product_type(self, request):
        """获取商品类型 JSON Schema（后端已解析，前端无需二次 JSON.parse）。

        Query params:
            marketplaceId: Amazon 市场 ID（如 A1PA6795UKMFR9）。
            productTypeOrigin: 商品类型标识（如 SHIRT）。

        Returns:
            ProductTypeSchemaSerializer 序列化后的数据，包含：
            - requiredFields: 根级必填字段名列表
            - defaultFields: $defs 中 marketplace_id / language_tag 默认值
            - fields: 站点语言版本字段定义
            - fieldsZh: 中文版本字段定义
        """
        marketplace_id = request.query_params.get("marketplaceId", "").strip()
        product_type_origin = request.query_params.get("productTypeOrigin", "").strip()

        if not marketplace_id or not product_type_origin:
            return drf_error("marketplaceId 和 productTypeOrigin 不能为空", status=400)

        schema = get_product_type_schema(marketplace_id, product_type_origin)
        if schema is None:
            return drf_error(
                f"未找到商品类型 Schema：marketplaceId={marketplace_id}, "
                f"productTypeOrigin={product_type_origin}",
                status=404,
            )

        logger.info(
            "[ProductTypeSchemaViewSet] [get_product_type] 查询成功：%s (%s)",
            schema.display_name,
            schema.product_type_origin,
        )
        return drf_ok(ProductTypeSchemaSerializer(schema).data)
