"""负责人列表接口（使用 LxUser 模型）。"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.lingxing_basic.models.lx_user import LxUser
from apps.common.utils.responses import drf_ok


class OwnerOptionsViewSet(viewsets.ViewSet):
    """负责人下拉数据源。"""

    permission_classes = [IsAuthenticated]

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
