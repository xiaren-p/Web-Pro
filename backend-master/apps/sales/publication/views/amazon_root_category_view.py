"""Amazon 根分类视图。

提供三个只读接口：根分类列表、子分类列表、分类搜索。
所有接口均以 marketplaceId 为必填参数，由前端从店铺下拉中获取。

路由前缀：api/v1/sales/（由 backend_master/urls.py 的 include 提供）
"""
import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.utils.responses import drf_error, drf_ok
from apps.sales.publication.selectors.amazon_root_category_selector import (
    get_root_categories,
    get_category_children,
    search_categories,
)
from apps.sales.publication.serializers.amazon_root_category_serializer import (
    AmazonRootCategorySerializer,
)

logger = logging.getLogger(__name__)


class AmazonRootCategoryViewSet(viewsets.ViewSet):
    """Amazon 分类查询接口。

    路由前缀：/sales/root-categories, /sales/category-children, /sales/category-search
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="")
    def root_categories(self, request):
        """获取指定市场的根分类列表。

        Query params:
            marketplaceId: Amazon 市场 ID（必填）。

        Returns:
            根分类数组，每个含 categoryUniqueId / categoryName / hasChildren / productTypeOrigin 等。
        """
        marketplace_id = request.query_params.get("marketplaceId", "").strip()
        if not marketplace_id:
            return drf_error("marketplaceId 不能为空", status=400)

        categories = get_root_categories(marketplace_id)
        logger.info(
            "[AmazonRootCategoryViewSet] [root_categories] marketplaceId=%s, 返回 %d 条",
            marketplace_id,
            len(categories),
        )
        return drf_ok(AmazonRootCategorySerializer(categories, many=True).data)

    @action(detail=False, methods=["get"], url_path="children")
    def category_children(self, request):
        """获取指定分类的子分类列表。

        Query params:
            marketplaceId: Amazon 市场 ID（必填）。
            categoryUniqueId: 父分类唯一 ID（必填）。

        Returns:
            子分类数组。
        """
        marketplace_id = request.query_params.get("marketplaceId", "").strip()
        category_unique_id = request.query_params.get("categoryUniqueId", "").strip()

        if not marketplace_id or not category_unique_id:
            return drf_error("marketplaceId 和 categoryUniqueId 不能为空", status=400)

        children = get_category_children(marketplace_id, category_unique_id)
        logger.info(
            "[AmazonRootCategoryViewSet] [category_children] marketplaceId=%s, categoryUniqueId=%s, 返回 %d 条",
            marketplace_id,
            category_unique_id,
            len(children),
        )
        return drf_ok(AmazonRootCategorySerializer(children, many=True).data)

    @action(detail=False, methods=["get"], url_path="search")
    def category_search(self, request):
        """按关键词搜索分类。

        Query params:
            marketplaceId: Amazon 市场 ID（必填）。
            searchType: 搜索类型（category_name / product_type_origin / category_id，默认 category_name）。
            keyword: 搜索关键词（必填）。

        Returns:
            匹配的分类数组（最多 200 条）。
        """
        marketplace_id = request.query_params.get("marketplaceId", "").strip()
        search_type = request.query_params.get("searchType", "category_name").strip()
        keyword = request.query_params.get("keyword", "").strip()

        if not marketplace_id or not keyword:
            return drf_error("marketplaceId 和 keyword 不能为空", status=400)

        results = search_categories(marketplace_id, search_type, keyword)
        logger.info(
            "[AmazonRootCategoryViewSet] [category_search] marketplaceId=%s, searchType=%s, keyword=%s, 返回 %d 条",
            marketplace_id,
            search_type,
            keyword,
            len(results),
        )
        return drf_ok(AmazonRootCategorySerializer(results, many=True).data)
