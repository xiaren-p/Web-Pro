"""获取店铺列表与负责人列表（使用 LxShops + LxUser 模型）。"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from api_v1.models import LxShops, LxUser
from api_v1.utils.responses import drf_ok


class ShopOptionsViewSet(viewsets.ViewSet):
    """店铺与负责人下拉数据源。"""

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

    @action(detail=False, methods=["get"], url_path="owners")
    def owners(self, request):
        """返回领星用户负责人列表供前端下拉使用。"""
        qs = (
            LxUser.objects
            .filter(status=1)
            .exclude(realname__isnull=True)
            .exclude(realname="")
            .order_by("realname")
        )
        out = []
        for u in qs:
            out.append({
                "uid": u.uid,
                "value": u.uid,
                "label": u.realname or u.username or str(u.uid),
                "name": u.realname or u.username or str(u.uid),
            })
        return drf_ok(out)
