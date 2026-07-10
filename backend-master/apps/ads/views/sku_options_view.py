"""SKU 搜索下拉数据视图。

提供 SKU/ASIN/MSKU 搜索下拉选项数据，数据由 Celery 定时任务
``refresh_listing_caches`` 预热到 Redis，搜索在内存中毫秒级过滤。
"""
from __future__ import annotations

from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.utils.responses import drf_ok


class SkuOptionsViewSet(viewsets.ViewSet):
    """SKU/ASIN/MSKU 搜索下拉数据源。

    从 Redis 缓存中读取预热后的全量 SKU 数据，根据关键词在
    内存中进行毫秒级模糊匹配（支持 value / code / title 三个字段）。
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="sku-options")
    def sku_options(self, request: Request) -> Response:
        """获取 SKU/ASIN/MSKU 搜索下拉选项数据。

        数据由 Celery 定时任务 ``refresh_listing_caches`` 预热到 Redis，
        搜索在内存中毫秒级过滤。

        Args:
            request: DRF 请求对象，body 中 ``keyword`` 为可选搜索关键词。

        Returns:
            包含 ``skus`` 列表的响应，每项包含 value / code / title 等字段。
        """
        keyword = (request.data.get("keyword") or "").strip().lower()

        all_skus: list[dict] = cache.get("sku_options_cache_v1") or []

        if keyword:
            result = [s for s in all_skus
                      if keyword in str(s.get("value", "")).lower()
                      or keyword in str(s.get("code", "")).lower()
                      or keyword in str(s.get("title", "")).lower()]
        else:
            result = all_skus

        return drf_ok({"skus": result})
