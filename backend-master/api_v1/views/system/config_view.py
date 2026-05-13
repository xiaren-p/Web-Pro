"""参数配置 ViewSet。

按钮级权限映射：

- 查询: ``sys:config:query`` -> page / list_or_create(GET) / form
- 新增: ``sys:config:add`` -> list_or_create(POST)
- 编辑: ``sys:config:edit`` -> update_or_delete(PUT)
- 删除: ``sys:config:delete`` -> update_or_delete(DELETE)

刷新缓存暂归入查询权限（需要看到菜单即可）。
"""
from __future__ import annotations

from typing import Any

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models import Config
from api_v1.permissions import MenuPermRequired
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


class ConfigViewSet(viewsets.ViewSet):
    """参数配置接口。"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action_name = getattr(self, "action", None)
        method = (
            getattr(self.request, "method", "").upper()
            if hasattr(self, "request") else ""
        )
        required: list[str] | None = None
        if action_name in ("page", "form") or (action_name == "list_or_create" and method == "GET"):
            required = ["sys:config:query"]
        elif action_name == "list_or_create" and method == "POST":
            required = ["sys:config:add"]
        elif action_name == "update_or_delete" and method == "PUT":
            required = ["sys:config:edit"]
        elif action_name == "update_or_delete" and method == "DELETE":
            required = ["sys:config:delete"]
        elif action_name == "refresh_cache":
            required = ["sys:config:query"]
        setattr(self, "required_perms", required)
        return super().get_permissions()

    @staticmethod
    def _serialize(conf: Config) -> dict[str, Any]:
        """单条参数序列化为前端可直接渲染结构。

        简化处理：使用 ``key`` 作为 ``configName`` 名称展示。
        """
        return {
            "id": conf.id,
            "configName": conf.key,
            "configKey": conf.key,
            "configValue": conf.value,
            "status": 1 if conf.status else 0,
            "remark": conf.remark,
        }

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request: Request) -> Any:
        """参数分页查询（关键字匹配 key/value）。"""
        qs = Config.objects.all().order_by("id")
        kw = request.query_params.get("keywords")
        if kw:
            qs = qs.filter(Q(key__icontains=kw) | Q(value__icontains=kw))
        total, items, _, _ = paginate_queryset(request, qs)
        return drf_ok({"total": total, "list": [self._serialize(c) for c in items]})

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request: Request) -> Any:
        """GET: 全量参数列表；POST: 新增参数。"""
        if request.method.lower() == "get":
            items = Config.objects.all().order_by("id")
            return drf_ok([self._serialize(c) for c in items])

        p = request.data.copy()
        key = p.get("configKey") or p.get("key") or p.get("configName")
        value = p.get("configValue") or p.get("value") or ""
        remark = p.get("remark") or ""
        status = p.get("status", 1)
        c = Config.objects.create(
            key=key or "", value=value, remark=remark,
            status=bool(int(status)) if isinstance(status, (str, int)) else bool(status),
        )
        return drf_ok(self._serialize(c), status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request: Request, id: str) -> Any:
        """获取参数表单数据（用于编辑回填）。"""
        try:
            c = Config.objects.get(pk=id)
        except Config.DoesNotExist:
            return drf_error("未找到参数", status=404)
        return drf_ok(self._serialize(c))

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request: Request, ids: str) -> Any:
        """PUT: 更新参数；DELETE: 批量删除（逗号分隔 ID）。"""
        if request.method.lower() == "put":
            first_id = ids.split(",")[0]
            try:
                c = Config.objects.get(pk=first_id)
            except Config.DoesNotExist:
                return drf_error("未找到参数", status=404)
            p = request.data.copy()
            if "configKey" in p or "key" in p or "configName" in p:
                c.key = p.get("configKey") or p.get("key") or p.get("configName") or c.key
            if "configValue" in p or "value" in p:
                c.value = p.get("configValue") or p.get("value") or c.value
            if "remark" in p:
                c.remark = p.get("remark") or c.remark
            if "status" in p:
                s = p.get("status")
                c.status = bool(int(s)) if isinstance(s, (str, int)) else bool(s)
            c.save()
            return drf_ok(self._serialize(c))

        id_list = [i for i in ids.split(",") if i]
        Config.objects.filter(id__in=id_list).delete()
        return drf_ok(status=204)

    @action(detail=False, methods=["post"], url_path="refresh-cache")
    def refresh_cache(self, request: Request) -> Any:
        """刷新参数缓存（占位实现，目前直接返回成功）。"""
        return drf_ok({"message": "refreshed"})
