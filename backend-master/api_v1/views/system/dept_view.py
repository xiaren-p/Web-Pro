"""部门管理 ViewSet。"""
from __future__ import annotations

from typing import Any

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models import Department
from api_v1.permissions import MenuPermRequired
from api_v1.serializers import DeptSerializer
from api_v1.utils.responses import drf_error, drf_ok
from api_v1.services.nc.nc_sync_service import NcSyncService


class DeptViewSet(viewsets.ViewSet):
    """部门管理接口。"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action_name = getattr(self, "action", None)
        method = (
            getattr(self.request, "method", "").upper()
            if hasattr(self, "request") else ""
        )
        required: list[str] | None = None
        if action_name in ("list_or_create", "tree", "options", "form") and method == "GET":
            required = ["sys:dept:query"]
        elif action_name == "list_or_create" and method == "POST":
            required = ["sys:dept:add"]
        elif action_name == "update_or_delete" and method == "PUT":
            required = ["sys:dept:edit"]
        elif action_name == "update_or_delete" and method == "DELETE":
            required = ["sys:dept:delete"]
        setattr(self, "required_perms", required)
        return super().get_permissions()

    def _build_tree(self, nodes: list[Department]) -> list[dict[str, Any]]:
        """构建部门树形结构（带循环检测保护）。"""
        by_parent: dict[int, list[Department]] = {}
        for d in nodes:
            pid = d.parent_id or 0
            by_parent.setdefault(pid, []).append(d)

        def build(pid: int | None = None, path: set[int] | None = None) -> list[dict[str, Any]]:
            if path is None:
                path = set()
            res: list[dict[str, Any]] = []
            for d in by_parent.get(pid or 0, []):
                if d.id in path:
                    continue
                new_path = set(path)
                new_path.add(d.id)
                res.append({
                    "id": d.id,
                    "parentId": d.parent_id,
                    "name": d.name,
                    "code": getattr(d, "code", ""),
                    "status": 1 if d.status else 0,
                    "sort": d.order_num,
                    "children": build(d.id, new_path),
                })
            return res

        return build(None)

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request: Request) -> Any:
        """GET: 部门列表（关键字 / 状态筛选）；POST: 新增部门。"""
        if request.method.lower() == "get":
            qs = Department.objects.all().order_by("order_num", "id")
            keyword = (
                request.query_params.get("keyword")
                or request.query_params.get("keywords")
            )
            if isinstance(keyword, str):
                kw = keyword.strip()
                if kw:
                    qs = qs.filter(Q(name__icontains=kw) | Q(code__icontains=kw))
            status_val = request.query_params.get("status")
            if status_val is not None and status_val != "":
                try:
                    qs = qs.filter(status=bool(int(status_val)))
                except Exception:
                    pass
            return drf_ok(DeptSerializer(qs, many=True).data)

        payload = request.data.copy()
        name = payload.get("name")
        parent_id = payload.get("parentId")
        sort = payload.get("sort", 0)
        status = payload.get("status", 1)
        code = payload.get("code", "")
        dept = Department.objects.create(
            name=name or "",
            parent=Department.objects.filter(pk=parent_id).first() if parent_id else None,
            order_num=int(sort or 0),
            code=code or "",
            status=bool(int(status)) if isinstance(status, (str, int)) else bool(status),
        )
        NcSyncService.on_dept_created(dept)
        return drf_ok({"id": dept.id}, status=201)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request: Request) -> Any:
        """部门树形结构。"""
        try:
            qs = Department.objects.all().order_by("order_num", "id")
            return drf_ok(self._build_tree(list(qs)))
        except Exception:
            return drf_error("服务器内部错误", status=500)

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request: Request) -> Any:
        """部门下拉选项。"""
        qs = Department.objects.filter(status=True).order_by("order_num", "id")
        return drf_ok([{"label": d.name, "value": d.id} for d in qs])

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request: Request, id: str) -> Any:
        """获取部门表单数据（用于编辑回填）。"""
        try:
            d = Department.objects.get(pk=id)
        except Department.DoesNotExist:
            return drf_error("未找到部门", status=404)
        return drf_ok({
            "id": d.id, "name": d.name,
            "code": getattr(d, "code", ""),
            "parentId": d.parent_id,
            "status": 1 if d.status else 0,
            "sort": d.order_num,
        })

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request: Request, ids: str) -> Any:
        """PUT: 更新部门（带循环引用检查）；DELETE: 批量删除（逗号分隔 ID）。"""
        if request.method.lower() == "put":
            first_id = ids.split(",")[0]
            try:
                d = Department.objects.get(pk=first_id)
            except Department.DoesNotExist:
                return drf_error("未找到部门", status=404)
            payload = request.data.copy()
            d.name = payload.get("name", d.name)
            parent_id = payload.get("parentId")
            # 校验：禁止将上级设置为自身或其子孙，避免循环
            if parent_id:
                try:
                    pid_int = int(parent_id)
                except Exception:
                    pid_int = None
                if pid_int and pid_int == d.id:
                    return drf_error("上级部门不能为自身", status=400)
                new_parent = Department.objects.filter(pk=parent_id).first()
                cur = new_parent
                while cur is not None:
                    if cur.id == d.id:
                        return drf_error("上级部门不能为其子孙节点", status=400)
                    cur = cur.parent
                d.parent = new_parent
            else:
                d.parent = None
            if "sort" in payload:
                d.order_num = int(payload.get("sort") or 0)
            if "code" in payload:
                d.code = payload.get("code") or ""
            if "status" in payload:
                s = payload.get("status")
                d.status = bool(int(s)) if isinstance(s, (str, int)) else bool(s)
            d.save()
            NcSyncService.on_dept_updated(d)
            return drf_ok({"id": d.id})

        id_list = [i for i in ids.split(",") if i]
        # \u5148\u5165\u961f NC \u7fa4\u7ec4\u5220\u9664\uff08\u672c\u5730 NcGroup \u955c\u50cf\u4e5f\u4f1a\u88ab\u540c\u6b65\u5220\u9664\uff09\uff0c\u518d\u5220\u9664\u90e8\u95e8\u8bb0\u5f55\n        for dept_id in id_list:
            try:
                NcSyncService.on_dept_deleted(int(dept_id))
            except Exception:
                # \u4e0d\u963b\u65ad\u90e8\u95e8\u5220\u9664\u4e3b\u6d41\u7a0b
                pass
        Department.objects.filter(id__in=id_list).delete()
        return drf_ok(status=204)
