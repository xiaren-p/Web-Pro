"""Amazon 市场列表视图。

从 LxMarketplace 模型返回市场下拉数据，供模板编辑页选择国家/市场。

路由前缀：api/v1/sales/publication/marketplaces
"""
import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.utils.responses import drf_ok
from apps.lingxing_basic.models.lx_marketplace import LxMarketplace

logger = logging.getLogger(__name__)


class MarketplaceViewSet(viewsets.ViewSet):
    """Amazon 市场列表接口。

    路由前缀：/sales/publication/marketplaces
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="")
    def list_marketplaces(self, request):
        """返回全部 Amazon 市场列表，供前端下拉使用。

        Returns:
            ``[{ marketplaceId, country, code, region, awsRegion }]``。
        """
        qs = LxMarketplace.objects.all().order_by("mid")
        out = [
            {
                "marketplaceId": m.marketplace_id,
                "country": m.country or "",
                "code": m.code or "",
                "region": m.region or "",
                "awsRegion": m.aws_region or "",
            }
            for m in qs
        ]
        logger.info("[MarketplaceViewSet] [list_marketplaces] 返回 %d 条", len(out))
        return drf_ok(out)
