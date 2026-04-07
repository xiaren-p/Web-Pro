"""角色管理视图。

模块说明：提供角色的分页、选项、详情、新增、修改、删除以及分配菜单权限接口。
"""

import json
import time

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action

from api_v1.models import Role, Menu
from api_v1.serializers import RoleSerializer, RoleWriteSerializer
from api_v1.utils.responses import drf_ok, drf_error
from api_v1.utils.pagination import paginate_queryset

class RoleViewSet(viewsets.ViewSet):
    """角色管理接口

    路由前缀：/roles
    支持：分页列表、下拉选项、详情、新增、修改、删除、分配菜单权限
    """

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        qs = Role.objects.all().order_by("order_num", "id")
        kw = request.query_params.get("keywords")
        if kw:
            qs = qs.filter(Q(name__icontains=kw) | Q(code__icontains=kw))
        status = request.query_params.get("status")
        if status is not None:
            qs = qs.filter(status=bool(int(status)))
        total, items, _, _ = paginate_queryset(request, qs)
        data = RoleSerializer(items, many=True).data
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        qs = Role.objects.filter(status=True).order_by("order_num", "id")
        data = [{"label": r.name, "value": r.id} for r in qs]
        return drf_ok(data)

    @action(detail=False, methods=["get"], url_path=r"(?P<role_id>[^/]+)/form")
    def form(self, request, role_id: str):
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return drf_error("未找到角色", status=404)
        return drf_ok(RoleSerializer(role).data)

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == 'get':
            items = Role.objects.all().order_by("order_num", "id")
            data = RoleSerializer(items, many=True).data
            return drf_ok(data)
        
        # POST
        t0 = time.perf_counter()
        s = RoleWriteSerializer(data=request.data)
        if s.is_valid():
            role = s.save()
            return drf_ok(RoleSerializer(role).data, status=201)
        return drf_error("参数错误", data=s.errors, status=400)

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == 'put':
            t0 = time.perf_counter()
            try:
                role = Role.objects.get(pk=ids) # Assuming single ID for PUT based on URL pattern
            except Role.DoesNotExist:
                return drf_error("未找到角色", status=404)
            s = RoleWriteSerializer(role, data=request.data, partial=True)
            if s.is_valid():
                s.save()
                return drf_ok(RoleSerializer(role).data)
            return drf_error("参数错误", data=s.errors, status=400)
        
        # DELETE
        t0 = time.perf_counter()
        id_list = ids.split(",")
        cnt = Role.objects.filter(id__in=id_list).delete()
        return drf_ok({'message': '删除成功'})

    @action(detail=False, methods=["get"], url_path=r"(?P<role_id>[^/]+)/menus")
    def menu_ids(self, request, role_id: str):
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return drf_error("未找到角色", status=404)
        mids = list(role.menus.values_list("id", flat=True))
        return drf_ok(mids)

    @action(detail=False, methods=["put"], url_path=r"(?P<role_id>[^/]+)/menus")
    def update_menus(self, request, role_id: str):
        t0 = time.perf_counter()
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return drf_error("未找到角色", status=404)
        menu_ids = request.data or []
        # 前端可能传 [1, 2, 3]
        role.menus.set(Menu.objects.filter(id__in=menu_ids))
        return drf_ok({'message': '菜单权限已更新'})
