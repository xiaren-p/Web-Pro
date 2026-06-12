"""广告通用组合数据视图（AdPortfolio）。"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import LxAdsPortfolio
from api_v1.utils.responses import drf_ok


class AdPortfolioViewSet(viewsets.ViewSet):
    """广告组合数据视图。"""

    @action(detail=False, methods=["post"], url_path="options")
    def options(self, request: Request) -> Response:
        """获取广告组合下拉选项数据。

        Args:
            request (Request): DRF 原始请求对象。

        Returns:
            Response: 包含广告组合（``portfolios``）映射列表。
        """
        # 新模型 portfolio_id 非唯一（联合唯一键 (portfolio_id, profile_id)），
        # values_list + distinct 按 portfolio_id 去重，避免下拉选项重复。
        portfolios_qs = LxAdsPortfolio.objects.values_list("portfolio_id", "name").distinct()
        keyword = request.data.get("keyword")
        if keyword:
            portfolios_qs = portfolios_qs.filter(name__icontains=keyword)

        portfolios = []
        for pid, p_name in portfolios_qs:
            if pid:
                portfolios.append({
                    "value": str(pid),
                    "label": p_name if p_name else str(pid),
                })

        return drf_ok({"portfolios": portfolios})
