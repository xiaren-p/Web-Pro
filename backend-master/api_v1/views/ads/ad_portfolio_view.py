"""广告组合数据视图（AdPortfolio）。"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import LxAdPortfolios
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
        portfolios_qs = LxAdPortfolios.objects.all()
        keyword = request.data.get("keyword")
        if keyword:
            portfolios_qs = portfolios_qs.filter(name__icontains=keyword)

        portfolios = []
        for p in portfolios_qs:
            if p.portfolio_id:
                portfolios.append({
                    "value": str(p.portfolio_id),
                    "label": p.name if p.name else str(p.portfolio_id),
                })

        return drf_ok({"portfolios": portfolios})
