import traceback
import time
from typing import List

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.utils.responses import drf_ok, drf_error
from api_v1.models import LxSellers, LxShops
# write_log 调用已移除
from concurrent.futures import TimeoutError as FuturesTimeout


class SellerViewSet(viewsets.ViewSet):
    """获取授权店铺与负责人列表。"""

    def get_permissions(self):
        # GET 列表接口允许匿名访问以便前端取下拉；如需鉴权请改为 IsAuthenticated
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        if method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        try:
            qs = LxSellers.objects.all()
            out: List[dict] = []
            
            for item in qs:
                sid = item.id
                name = item.name or str(item.id)
                country_code = item.country_code or ''
                country = item.country or ''
                
                out.append({
                    'id': sid,
                    'name': name,
                    'country': country, 
                    'label': name,
                    'label_extra': country,
                    'raw': {
                        'profile_id': item.id,
                        'alias': item.name,
                        'country': country_code, 
                        'type': item.is_concept
                    },
                })
            
            return drf_ok(out)

        except Exception as e:
            tb = traceback.format_exc()
            return drf_error('获取店铺数据失败', status=500, data={'msg': str(e), 'trace': tb})

    @action(detail=False, methods=["get"], url_path="owners")
    def owners(self, request):
        """直接从数据库 lx_shops 获取卖家账号负责人列表返回前端。"""
        try:
            qs = (
                LxShops.objects
                .exclude(seller_account_id__isnull=True)
                .exclude(account_name__isnull=True)
                .exclude(account_name="")
                .values("seller_account_id", "account_name")
                .distinct()
                .order_by("account_name")
            )
            out: List[dict] = []

            for item in qs:
                uid = item["seller_account_id"]
                name = item["account_name"] or str(uid)
                out.append({
                    "id": uid,
                    "uid": uid,
                    "value": uid,
                    "label": name,
                    "name": name,
                    "name_zh": name,
                    "raw": {
                        "uid": uid,
                        "seller_account_id": uid,
                        "name": name,
                        "name_zh": name,
                    },
                })

            return drf_ok(out)

        except Exception as e:
            tb = traceback.format_exc()
            return drf_error('获取负责人数据失败', status=500, data={'msg': str(e), 'trace': tb})
