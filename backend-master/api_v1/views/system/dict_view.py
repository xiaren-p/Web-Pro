"""字典与字典项 ViewSet。"""
from __future__ import annotations

from typing import Any

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models import DictItem, DictType
from api_v1.permissions import MenuPermRequired
from api_v1.serializers import DictItemSerializer, DictTypeSerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


def _parse_status(v: Any, default: bool = True) -> bool:
    """通用 status 解析：兼容 ``True/False/0/1/"0"/"1"/None/""/"null"`` 等输入。"""
    if v in (None, "", "null"):
        return default
    if isinstance(v, (str, int)):
        try:
            return bool(int(v))
        except Exception:
            return default
    return bool(v)


class DictViewSet(viewsets.ViewSet):
    """字典与字典项接口。"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action_name = getattr(self, "action", None)
        method = (
            getattr(self.request, "method", "").upper()
            if hasattr(self, "request") else ""
        )
        required: list[str] | None = None
        if action_name in ("page", "list_or_create", "form", "items_page", "item_form") and method == "GET":
            required = ["sys:dict:query"]
        # 字典项选项接口单独使用 sys:dict:item 更细粒度权限
        elif action_name == "item_options" and method == "GET":
            required = ["sys:dict:item"]
        elif action_name == "list_or_create" and method == "POST":
            required = ["sys:dict:add"]
        elif action_name == "update_or_delete" and method == "PUT":
            required = ["sys:dict:edit"]
        elif action_name == "update_or_delete" and method == "DELETE":
            required = ["sys:dict:delete"]
        elif action_name == "items_list_or_create" and method == "POST":
            required = ["sys:dict:add"]
        elif action_name == "item_update_or_delete" and method == "PUT":
            required = ["sys:dict:edit"]
        elif action_name == "item_update_or_delete" and method == "DELETE":
            required = ["sys:dict:delete"]
        setattr(self, "required_perms", required)
        return super().get_permissions()

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request: Request) -> Any:
        """字典类型分页列表。统一将 status 转换为 1/0 数值，前端可直接严格比较。"""
        qs = DictType.objects.all().order_by("id")
        kw = request.query_params.get("keywords")
        if kw:
            qs = qs.filter(Q(name__icontains=kw) | Q(code__icontains=kw))
        total, items, _, _ = paginate_queryset(request, qs)
        data = DictTypeSerializer(items, many=True).data
        for d in data:
            try:
                d["status"] = 1 if d.get("status") else 0
            except Exception:
                d["status"] = 0
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request: Request) -> Any:
        """GET: 字典类型全量列表；POST: 新增字典类型。"""
        if request.method.lower() == "get":
            items = DictType.objects.all().order_by("id")
            data = [
                {
                    "id": d.id,
                    "name": d.name,
                    "dictCode": d.code,
                    "status": 1 if d.status else 0,
                }
                for d in items
            ]
            return drf_ok(data)

        payload = request.data.copy()
        name = payload.get("name")
        code = payload.get("dictCode") or payload.get("code")
        status_raw = payload.get("status", 1)
        dt = DictType.objects.create(
            name=name or "", code=code or "",
            status=_parse_status(status_raw, True),
        )
        return drf_ok({"id": dt.id}, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request: Request, id: str) -> Any:
        """获取字典类型表单数据（用于编辑回填）。"""
        try:
            d = DictType.objects.get(pk=id)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        return drf_ok({
            "id": d.id, "name": d.name,
            "dictCode": d.code, "status": 1 if d.status else 0,
        })

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request: Request, ids: str) -> Any:
        """PUT: 更新字典类型；DELETE: 批量删除（逗号分隔 ID）。"""
        if request.method.lower() == "put":
            first_id = ids.split(",")[0]
            try:
                d = DictType.objects.get(pk=first_id)
            except DictType.DoesNotExist:
                return drf_error("未找到字典", status=404)
            payload = request.data.copy()
            if "name" in payload:
                d.name = payload.get("name") or d.name
            if "dictCode" in payload or "code" in payload:
                d.code = payload.get("dictCode") or payload.get("code") or d.code
            if "status" in payload:
                d.status = _parse_status(payload.get("status"), d.status)
            d.save()
            return drf_ok({"id": d.id})

        id_list = [i for i in ids.split(",") if i]
        DictType.objects.filter(id__in=id_list).delete()
        return drf_ok(status=204)

    # ─── 字典项相关接口 ───────────────────────────────

    @action(detail=False, methods=["get", "post"], url_path=r"(?P<dict_code>[^/]+)/items")
    def items_list_or_create(self, request: Request, dict_code: str) -> Any:
        """字典项 GET: 全量列表；POST: 新增字典项。"""
        try:
            dt = DictType.objects.get(code=dict_code)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        if not dt.status:
            return drf_error("字典已禁用", status=403)

        if request.method.lower() == "get":
            items = DictItem.objects.filter(dict_type=dt).order_by("sort", "id")
            return drf_ok(DictItemSerializer(items, many=True).data)

        payload = request.data.copy()
        i = DictItem.objects.create(
            dict_type=dt,
            label=payload.get("label") or "",
            value=payload.get("value") or "",
            sort=int(payload.get("sort") or 0),
            status=_parse_status(payload.get("status", 1), True),
            tag_type=payload.get("tagType") or payload.get("tag_type") or "",
        )
        return drf_ok({"id": i.id}, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<dict_code>[^/]+)/items/page")
    def items_page(self, request: Request, dict_code: str) -> Any:
        """字典项分页列表。"""
        try:
            dt = DictType.objects.get(code=dict_code)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        if not dt.status:
            return drf_error("字典已禁用", status=403)

        qs = DictItem.objects.filter(dict_type=dt).order_by("sort", "id")
        kw = request.query_params.get("keywords")
        if kw:
            qs = qs.filter(Q(label__icontains=kw) | Q(value__icontains=kw))
        total, items, _, _ = paginate_queryset(request, qs)
        data = DictItemSerializer(items, many=True).data
        # 兜底：确保 status 数值化（前端严格比较友好）
        for it in data:
            try:
                it["status"] = 1 if it.get("status") in (True, 1, "1", "true", "True") else 0
            except Exception:
                it["status"] = 0
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get"], url_path=r"(?P<dict_code>[^/]+)/items/(?P<item_id>[^/]+)/form")
    def item_form(self, request: Request, dict_code: str, item_id: str) -> Any:
        """获取字典项表单数据（用于编辑回填）。"""
        try:
            dt = DictType.objects.get(code=dict_code)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        if not dt.status:
            return drf_error("字典已禁用", status=403)
        try:
            i = DictItem.objects.get(pk=item_id, dict_type=dt)
        except DictItem.DoesNotExist:
            return drf_error("未找到字典项", status=404)
        return drf_ok({
            "id": i.id, "label": i.label, "value": i.value,
            "status": 1 if i.status else 0, "sort": i.sort,
            "tagType": getattr(i, "tag_type", ""),
        })

    @action(detail=False, methods=["get"], url_path=r"(?P<dict_code>[^/]+)/items/options")
    def item_options(self, request: Request, dict_code: str) -> Any:
        """字典项下拉选项（仅返回启用项，gender 字典缺失时内置兜底）。"""
        try:
            dt = DictType.objects.get(code=dict_code)
            if not dt.status:
                return drf_ok([])
            items = DictItem.objects.filter(dict_type=dt, status=True).order_by("sort", "id")
            return drf_ok([{"label": i.label, "value": i.value} for i in items])
        except DictType.DoesNotExist:
            if dict_code == "gender":
                # 内置兜底：常用字典 gender 缺失时返回默认选项
                return drf_ok([
                    {"label": "男", "value": 1},
                    {"label": "女", "value": 2},
                    {"label": "保密", "value": 0},
                ])
            return drf_error("未找到字典", status=404)

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<dict_code>[^/]+)/items/(?P<item_id>[^/]+)")
    def item_update_or_delete(self, request: Request, dict_code: str, item_id: str) -> Any:
        """字典项 PUT: 更新；DELETE: 批量删除（逗号分隔 ID）。"""
        try:
            dt = DictType.objects.get(code=dict_code)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        if not dt.status:
            return drf_error("字典已禁用", status=403)

        if request.method.lower() == "put":
            try:
                i = DictItem.objects.get(pk=item_id, dict_type=dt)
            except DictItem.DoesNotExist:
                return drf_error("未找到字典项", status=404)
            payload = request.data.copy()
            if "label" in payload:
                i.label = payload.get("label") or i.label
            if "value" in payload:
                i.value = payload.get("value") or i.value
            if "sort" in payload:
                i.sort = int(payload.get("sort") or 0)
            if "status" in payload:
                s = payload.get("status")
                if s not in (None, "", "null"):
                    try:
                        i.status = bool(int(s))
                    except Exception:
                        i.status = True if s else i.status
            if "tagType" in payload or "tag_type" in payload:
                tv = payload.get("tagType") or payload.get("tag_type")
                i.tag_type = tv or ""
            i.save()
            return drf_ok({"id": i.id})

        # delete：单 id 与逗号分隔多 id 均支持
        id_list = [i for i in item_id.split(",") if i]
        DictItem.objects.filter(dict_type=dt, id__in=id_list).delete()
        return drf_ok(status=204)
