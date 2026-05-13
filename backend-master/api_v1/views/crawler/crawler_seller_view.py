"""卖家精灵账号配置视图（CrawlerSellerAccount）。"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.models import CrawlerSellerAccount
from api_v1.serializers import CrawlerSellerSerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


class CrawlerSellerViewSet(viewsets.ViewSet):
    """卖家精灵账号配置（对外开放，无需认证）。

    路由：
    - GET /crawler/seller -> 列表
    - POST /crawler/seller -> 新增
    - GET /crawler/seller/<id>/form -> 获取表单数据
    - PUT /crawler/seller/<ids> -> 更新
    - DELETE /crawler/seller/<ids> -> 删除
    """

    def get_permissions(self):
        method = getattr(self.request, "method", "").upper() if hasattr(self, "request") else ""
        if method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == "get":
            qs = CrawlerSellerAccount.objects.all().order_by("order_num", "id")
            kw = request.query_params.get("keywords") or request.query_params.get("keyword")
            if kw:
                try:
                    qs = qs.filter(username__icontains=str(kw).strip())
                except Exception:
                    pass
            total, items, _, _ = paginate_queryset(request, qs)
            data = CrawlerSellerSerializer(items, many=True).data
            if request.query_params.get("pageNum") or request.query_params.get("page"):
                return drf_ok({"total": total, "list": data})
            return drf_ok(data)

        # create
        payload = request.data or {}
        try:
            obj = CrawlerSellerAccount.objects.create(
                username=payload.get("username", "") or payload.get("userName", ""),
                password=payload.get("password", "") or payload.get("pwd", ""),
                status=int(payload.get("status", 1)),
                order_num=int(payload.get("order_num", 0) or payload.get("orderNum", 0)),
            )
            return drf_ok(CrawlerSellerSerializer(obj).data, status=201)
        except Exception as e:
            return drf_error("创建卖家账号失败", status=400, data={"msg": str(e)})

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        try:
            obj = CrawlerSellerAccount.objects.get(pk=id)
        except Exception:
            return drf_error("未找到配置", status=404)
        return drf_ok(CrawlerSellerSerializer(obj).data)

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == "put":
            first_id = ids.split(",")[0]
            try:
                conf = CrawlerSellerAccount.objects.get(pk=first_id)
            except Exception:
                return drf_error("未找到配置", status=404)
            p = request.data or {}
            if "username" in p or "userName" in p:
                conf.username = p.get("username") or p.get("userName") or conf.username
            if "password" in p or "pwd" in p:
                conf.password = p.get("password") or p.get("pwd") or conf.password
            if "status" in p:
                try:
                    conf.status = int(p.get("status"))
                except Exception:
                    conf.status = 1
            if "order_num" in p or "orderNum" in p:
                try:
                    conf.order_num = int(p.get("order_num") or p.get("orderNum") or conf.order_num)
                except Exception:
                    pass
            conf.save()
            return drf_ok(CrawlerSellerSerializer(conf).data)

        id_list = [i for i in ids.split(",") if i]
        CrawlerSellerAccount.objects.filter(id__in=id_list).delete()
        return drf_ok(status=204)
