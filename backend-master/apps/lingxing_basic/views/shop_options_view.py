"""店铺列表接口（使用 LxShops 模型）。"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.lingxing_basic.models.lx_shops import LxShops
from apps.common.utils.responses import drf_ok


class ShopOptionsViewSet(viewsets.ViewSet):
    """店铺下拉数据源。"""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="shops")
    def shops(self, request):
        """返回已启用且已配置广告的店铺列表供前端下拉使用。"""
        qs = (
            LxShops.objects
            .filter(status=1, has_ads_setting=1)
            .exclude(sid__isnull=True)
            .order_by("sid")
        )
        out = []
        for s in qs:
            out.append({
                "sid": s.sid,
                "name": s.name or str(s.sid),
                "country": s.country or "",
                "region": s.region or "",
                "account_name": s.account_name or "",
            })
        return drf_ok(out)
