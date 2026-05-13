"""数据采集节点配置视图（CrawlerConf）。"""
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.models import CrawlerConf
from api_v1.serializers import CrawlerConfSerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


class CrawlerConfViewSet(viewsets.ViewSet):
    """数据采集节点配置（对外开放，无需认证）。

    路由：
    - GET /crawler/conf -> 列表
    - POST /crawler/conf -> 新增
    - GET /crawler/conf/<id>/form -> 获取表单数据
    - PUT /crawler/conf/<ids> -> 更新（多个 id 传入逗号，以第一个为目标）
    - DELETE /crawler/conf/<ids> -> 删除
    """

    def get_permissions(self):
        """权限策略：GET 开放 AllowAny；写操作需要登录 IsAuthenticated。"""
        method = getattr(self.request, "method", "").upper() if hasattr(self, "request") else ""
        if method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == "get":
            qs = CrawlerConf.objects.all().order_by("order_num", "id")
            # 支持关键字搜索，匹配服务器名称或节点
            kw = request.query_params.get("keywords") or request.query_params.get("keyword")
            if kw:
                qs = qs.filter(Q(server_name__icontains=kw) | Q(node__icontains=kw))
            # 支持两种返回格式：
            # - 若前端传入分页参数（pageNum/pageSize），返回 {total, list}
            # - 否则返回数组以匹配部分旧前端组件的期望
            total, items, _, _ = paginate_queryset(request, qs)
            data = CrawlerConfSerializer(items, many=True).data
            if request.query_params.get("pageNum") or request.query_params.get("page"):
                return drf_ok({"total": total, "list": data})
            return drf_ok(data)
        # create
        payload = request.data or {}
        conf = CrawlerConf.objects.create(
            server_name=payload.get("server_name", "") or payload.get("serverName", ""),
            node=payload.get("node", ""),
            ip=payload.get("ip", ""),
            status=int(payload.get("status", 1)),
            order_num=int(payload.get("order_num", 0) or payload.get("orderNum", 0)),
        )
        return drf_ok(CrawlerConfSerializer(conf).data, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        import traceback
        try:
            conf = CrawlerConf.objects.get(pk=id)
            return drf_ok(CrawlerConfSerializer(conf).data)
        except CrawlerConf.DoesNotExist:
            return drf_error("未找到配置", status=404)
        except Exception as e:
            tb = traceback.format_exc()
            return drf_error("获取配置失败", status=500, data={"msg": str(e), "trace": tb})

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == "put":
            first_id = ids.split(",")[0]
            try:
                conf = CrawlerConf.objects.get(pk=first_id)
            except CrawlerConf.DoesNotExist:
                return drf_error("未找到配置", status=404)
            p = request.data or {}
            if "server_name" in p or "serverName" in p:
                conf.server_name = p.get("server_name") or p.get("serverName") or conf.server_name
            if "node" in p:
                conf.node = p.get("node") or conf.node
            if "ip" in p:
                conf.ip = p.get("ip") or conf.ip
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
            return drf_ok(CrawlerConfSerializer(conf).data)
        # delete
        id_list = [i for i in ids.split(",") if i]
        CrawlerConf.objects.filter(id__in=id_list).delete()
        return drf_ok(status=204)
