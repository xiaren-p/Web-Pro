"""部门管理 ViewSet。

模块说明：部门 CRUD + 树形结构 + 下拉选项。
写操作委托至 :mod:`apps.system.services.dept_write_service`。
"""
from __future__ import annotations

import logging
from typing import Any

from django.db.models import Q

logger = logging.getLogger(__name__)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from apps.system.models import Department
from apps.system.permissions import MenuPermRequired
from apps.system.serializers import DeptSerializer
from apps.common.utils.responses import drf_error, drf_ok
from apps.system.utils.dept_scope import get_caller_dept_ids
from apps.system.services.dept_write_service import create_dept, update_dept, delete_depts


class DeptViewSet(viewsets.ViewSet):
    """部门管理接口。"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        """返回当前 action 所需的权限类列表。"""
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
            """递归构建部门子树节点列表。

Args:
    pid (int | None): 父部门 ID，None 表示从根层级开始。
    path (set[int] | None): 已访问部门 ID 集合，用于循环引用检测。

Returns:
    list[dict[str, Any]]: 部门树节点列表（含 children）。
"""
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
            has_filter = False
            if isinstance(keyword, str):
                kw = keyword.strip()
                if kw:
                    qs = qs.filter(Q(name__icontains=kw) | Q(code__icontains=kw))
                    has_filter = True
            status_val = request.query_params.get("status")
            if status_val is not None and status_val != "":
                try:
                    qs = qs.filter(status=bool(int(status_val)))
                    has_filter = True
                except Exception:
                    pass
            nodes = list(qs)
            # 无过滤条件时返回树结构；有过滤时返回平铺列表（保留搜索结果可读性）
            if has_filter:
                return drf_ok(DeptSerializer(nodes, many=True).data)
            return drf_ok(self._build_tree(nodes))

        dept = create_dept(
            name=request.data.get("name"),
            parent_id=request.data.get("parentId"),
            sort=request.data.get("sort", 0),
            status=request.data.get("status", 1),
            code=request.data.get("code", ""),
        )
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
        """部门下拉选项。部门管理员仅返回自身及子部门，防止跨部门分配用户。"""
        dept_ids = get_caller_dept_ids(request.user)
        qs = Department.objects.filter(status=True).order_by("order_num", "id")
        if dept_ids is not None:
            qs = qs.filter(id__in=dept_ids)
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
            dept, err = update_dept(first_id, request.data)
            if err:
                return drf_error(err[0], status=err[1])
            return drf_ok({"id": dept.id})

        delete_depts(ids)
        return drf_ok(status=204)
