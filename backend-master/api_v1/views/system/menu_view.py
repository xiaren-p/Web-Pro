"""菜单与动态路由 ViewSet。"""
from __future__ import annotations

import re
from typing import Any

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models import Menu
from api_v1.permissions import MenuPermRequired
from api_v1.utils.responses import drf_error, drf_ok


class MenuViewSet(viewsets.ViewSet):
    """菜单与动态路由接口。"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action_name = getattr(self, "action", None)
        method = (
            getattr(self.request, "method", "").upper()
            if hasattr(self, "request")
            else ""
        )
        required: list[str] | None = None
        # 查询：列表 list_or_create(GET), tree, form 使用 菜单查询 权限；
        # options 下拉用于角色分配菜单场景，允许具备 菜单查询 或 角色编辑 任一权限访问（OR 逻辑）
        if action_name in ("list_or_create", "tree", "form") and method == "GET":
            required = ["sys:menu:query"]
        elif action_name == "options" and method == "GET":
            required = ["sys:menu:query", "sys:position:edit"]
        elif action_name == "list_or_create" and method == "POST":
            required = ["sys:menu:add"]
        elif action_name == "update_or_delete" and method == "PUT":
            required = ["sys:menu:edit"]
        elif action_name == "update_or_delete" and method == "DELETE":
            required = ["sys:menu:delete"]
        # routes 接口：用于动态路由加载，需要登录但不强制按钮级菜单权限
        elif action_name == "routes":
            required = None
        setattr(self, "required_perms", required)
        return super().get_permissions()

    @staticmethod
    def _serialize(m: Menu) -> dict[str, Any]:
        """菜单单条序列化为前端可直接渲染结构。"""

        def compute_route_name() -> str:
            # routeName 仅对"菜单"类型生效（type=2）。目录/按钮/外链不显示路由名称。
            if m.type != 2:
                return ""
            try:
                if m.route_name:
                    return m.route_name
                if m.component:
                    last = m.component.split("/")[-1]
                    return (last[:1].upper() + last[1:]) if last else f"Menu{m.id}"
                return f"Menu{m.id}"
            except Exception:
                return f"Menu{m.id}"

        return {
            "id": m.id,
            "parentId": m.parent_id,
            "name": m.name,
            "type": m.type,
            "routeName": compute_route_name(),
            "path": m.path,
            "component": m.component,
            "perms": m.perms,
            "icon": m.icon,
            "sort": m.order_num,
            "visible": 1 if m.visible else 0,
            "status": 1 if m.status else 0,
        }

    @staticmethod
    def _build_routes(nodes: list[Menu]) -> list[dict[str, Any]]:
        """根据菜单节点列表构建动态路由树。"""
        # 仅目录/菜单生成路由，按钮(3)跳过
        by_parent: dict[int, list[Menu]] = {}
        for m in nodes:
            if m.type == 3:
                continue
            pid = m.parent_id or 0
            by_parent.setdefault(pid, []).append(m)

        def build(pid: int | None = None) -> list[dict[str, Any]]:
            result = []
            for m in by_parent.get(pid or 0, []):
                route: dict[str, Any] = {
                    "name": (m.route_name or f"Menu{m.id}"),
                    "path": m.path or (
                        f"/m{m.id}" if m.parent_id is None else m.path or f"m{m.id}"
                    ),
                    "component": m.component if m.component else (
                        "Layout" if m.type == 1 else ""
                    ),
                    "meta": {
                        "title": m.name,
                        "icon": m.icon or None,
                        "hidden": False if m.visible else True,
                    },
                }
                # 外链型：转换绝对 URL 为内部占位路径 + meta.link
                if m.type == 4:
                    original_path = m.path or ""
                    if re.match(r"^https?://", original_path):
                        internal_path = f"/ext-{m.id}"
                        route["path"] = internal_path
                        route["component"] = "external/redirect"
                        route["meta"]["link"] = original_path
                    route["meta"]["external"] = True
                children = build(m.id)
                if children:
                    route["children"] = children
                result.append(route)
            return result

        return build(None)

    @action(detail=False, methods=["get"], url_path="routes")
    def routes(self, request: Request) -> Any:
        """根据当前登录用户角色，返回其可见的动态路由树。"""
        user = getattr(request, "user", None)
        all_active = list(Menu.objects.filter(status=True).order_by("order_num", "id"))
        if not user or not getattr(user, "is_authenticated", False):
            return drf_error("未登录", status=401)

        # COMPANY_ADMIN 或超级用户返回全部菜单
        from api_v1.models.system.user_profile import AdminLevel
        profile = None
        try:
            profile = getattr(user, "profile", None)
        except Exception:
            pass
        level = profile.admin_level if profile else AdminLevel.MEMBER

        if user.is_superuser or level == AdminLevel.COMPANY_ADMIN:
            return drf_ok(self._build_routes(all_active))

        # 岗位关联菜单
        if not profile or not profile.position_id:
            return drf_ok([])
        assigned = list(Menu.objects.filter(status=True, positions__id=profile.position_id).distinct())
        if not assigned:
            return drf_ok([])

        by_id = {m.id: m for m in all_active}
        selected = {m.id for m in assigned}
        # 向上补全父级
        for m in list(assigned):
            p = m.parent
            while p is not None:
                if p.id in selected:
                    break
                selected.add(p.id)
                p = p.parent
        nodes = [by_id[i] for i in selected if i in by_id]
        nodes.sort(key=lambda x: (x.order_num, x.id))
        return drf_ok(self._build_routes(nodes))

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request: Request) -> Any:
        """GET: 全量菜单列表（支持关键字搜索）；POST: 新增菜单。"""
        if request.method.lower() == "get":
            qs = Menu.objects.all().order_by("order_num", "id")
            keyword = (
                request.query_params.get("keyword")
                or request.query_params.get("keywords")
            )
            if isinstance(keyword, str):
                kw = keyword.strip()
                if kw:
                    qs = qs.filter(
                        Q(name__icontains=kw)
                        | Q(path__icontains=kw)
                        | Q(component__icontains=kw)
                        | Q(perms__icontains=kw)
                    )
            return drf_ok([self._serialize(m) for m in qs])

        p = request.data.copy()
        m = Menu.objects.create(
            name=p.get("name") or "",
            type=int(p.get("type") or 2),
            route_name=p.get("routeName") or "",
            path=p.get("path") or "",
            component=p.get("component") or "",
            perms=p.get("perms") or "",
            icon=p.get("icon") or "",
            parent=Menu.objects.filter(pk=p.get("parentId")).first()
            if p.get("parentId") else None,
            order_num=int(p.get("sort") or 0),
            visible=bool(int(p.get("visible", 1))),
        )
        return drf_ok(self._serialize(m), status=201)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request: Request) -> Any:
        """菜单树形结构。搜索命中时直接返回扁平列表，避免父节点缺失导致树断层。"""
        qs = Menu.objects.all().order_by("order_num", "id")
        keyword = (
            request.query_params.get("keyword")
            or request.query_params.get("keywords")
        )
        is_search = False
        if isinstance(keyword, str):
            kw = keyword.strip()
            if kw:
                is_search = True
                qs = qs.filter(
                    Q(name__icontains=kw)
                    | Q(path__icontains=kw)
                    | Q(component__icontains=kw)
                    | Q(perms__icontains=kw)
                )

        nodes = [self._serialize(m) for m in qs]

        def build(pid: int | None = None) -> list[dict[str, Any]]:
            res = []
            for node in nodes:
                if is_search:
                    return nodes
                current_pid = node["parentId"]
                if current_pid == pid:
                    children = build(node["id"])
                    if children:
                        node["children"] = children
                    res.append(node)
            return res

        return drf_ok(build(None))

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request: Request, id: str) -> Any:
        """获取菜单表单数据（用于编辑回填）。"""
        try:
            m = Menu.objects.get(pk=id)
        except Menu.DoesNotExist:
            return drf_error("未找到菜单", status=404)
        return drf_ok(self._serialize(m))

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<id>[^/]+)")
    def update_or_delete(self, request: Request, id: str) -> Any:
        """根据菜单 ID 进行 PUT 编辑或 DELETE 删除（禁止删除存在子菜单的节点）。"""
        if request.method.lower() == "put":
            try:
                m = Menu.objects.get(pk=id)
            except Menu.DoesNotExist:
                return drf_error("未找到菜单", status=404)
            p = request.data.copy()
            if "name" in p:
                m.name = p.get("name") or m.name
            if "type" in p:
                try:
                    m.type = int(p.get("type"))
                except Exception:
                    pass
            if "routeName" in p:
                m.route_name = p.get("routeName") or ""
            if "path" in p:
                m.path = p.get("path") or m.path
            if "component" in p:
                m.component = p.get("component") or m.component
            if "perms" in p:
                m.perms = p.get("perms") or m.perms
            if "icon" in p:
                m.icon = p.get("icon") or m.icon
            if "parentId" in p:
                m.parent = Menu.objects.filter(pk=p.get("parentId")).first() if p.get("parentId") else None
            if "sort" in p:
                m.order_num = int(p.get("sort") or 0)
            if "visible" in p:
                m.visible = bool(int(p.get("visible")))
            if "status" in p:
                m.status = bool(int(p.get("status")))
            m.save()
            return drf_ok(self._serialize(m))

        # delete
        if Menu.objects.filter(parent_id=id).exists():
            return drf_error("存在子菜单，无法删除", status=400)
        Menu.objects.filter(pk=id).delete()
        return drf_ok(status=204)

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request: Request) -> Any:
        """菜单下拉选项。

        - ``onlyParent=true``: 仅返回目录与菜单（用于上级菜单选择）。
        - ``scope=assignable``: 仅返回当前登录用户有权分配的菜单范围；
          超级管理员或 COMPANY_ADMIN 返回全量，其他人返回其岗位菜单。
        """
        from api_v1.models.system.user_profile import AdminLevel

        scope = request.query_params.get("scope", "")
        only_parent = request.query_params.get("onlyParent")

        if scope == "assignable":
            user = getattr(request, "user", None)
            profile = None
            try:
                profile = getattr(user, "profile", None)
            except Exception:
                pass
            is_full_admin = (user and user.is_superuser) or (
                profile and profile.admin_level == AdminLevel.COMPANY_ADMIN
            )
            if is_full_admin:
                qs = Menu.objects.all().order_by("order_num", "id")
            elif profile and profile.position_id:
                qs = Menu.objects.filter(
                    positions__id=profile.position_id
                ).order_by("order_num", "id")
            else:
                return drf_ok([])
        elif only_parent and str(only_parent).lower() == "true":
            qs = Menu.objects.filter(type__in=[1, 2]).order_by("order_num", "id")
        else:
            qs = Menu.objects.all().order_by("order_num", "id")

        def build(pid: int | None = None) -> list[dict[str, Any]]:
            res = []
            for m in qs:
                if m.parent_id == pid:
                    children = build(m.id)
                    item: dict[str, Any] = {"value": m.id, "label": m.name}
                    if children:
                        item["children"] = children
                    res.append(item)
            return res

        return drf_ok(build(None))
