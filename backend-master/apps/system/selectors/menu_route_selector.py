"""菜单路由树查询选择器。

提供动态路由树构建与菜单树形结构查询的只读逻辑。
供 ``MenuViewSet`` 调用，避免业务逻辑滞留在视图层。
"""
from __future__ import annotations

import re
from typing import Any

from apps.system.models import Menu
from apps.system.models.user_profile import AdminLevel


def build_routes(nodes: list[Menu]) -> list[dict[str, Any]]:
    """根据菜单节点列表构建动态路由树。

    仅目录/菜单生成路由，按钮(type=3)跳过。外链(type=4)生成 redirect 组件。

    Args:
        nodes (list[Menu]): 菜单查询集。

    Returns:
        list[dict[str, Any]]: 路由节点列表（含 children）。
    """
    by_parent: dict[int, list[Menu]] = {}
    for m in nodes:
        if m.type == 3:
            continue
        pid = m.parent_id or 0
        by_parent.setdefault(pid, []).append(m)

    def build(pid: int | None = None) -> list[dict[str, Any]]:
        """递归构建路由子树。"""
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


def get_user_routes(user, profile) -> list[dict[str, Any]]:
    """获取用户可见的动态路由树。

    根据 admin_level 和岗位关联菜单计算可见路由：
    - COMPANY_ADMIN / 超级用户：返回全部
    - 有岗位用户：返回岗位关联菜单 + 祖先链补全

    Args:
        user: Django User 实例。
        profile: UserProfile 实例或 None。

    Returns:
        list[dict[str, Any]]: 路由节点列表。
    """
    all_active = list(Menu.objects.filter(status=True).select_related("parent").order_by("order_num", "id"))

    if not user or not getattr(user, "is_authenticated", False):
        return []

    level = profile.admin_level if profile else AdminLevel.MEMBER

    if user.is_superuser or level == AdminLevel.COMPANY_ADMIN:
        return build_routes(all_active)

    if not profile or not profile.position_id:
        return []

    assigned = list(Menu.objects.filter(status=True, positions__id=profile.position_id).distinct())
    if not assigned:
        return []

    by_id = {m.id: m for m in all_active}
    selected: set[int] = set()
    for m in assigned:
        selected.add(m.id)
        p = m.parent
        while p is not None:
            if p.id in selected:
                break
            selected.add(p.id)
            p = p.parent

    complete_routes = [by_id[mid] for mid in selected if mid in by_id]
    complete_routes.sort(key=lambda x: (x.order_num or 0, x.id))
    return build_routes(complete_routes)


def build_menu_tree(nodes: list[Menu]) -> list[dict[str, Any]]:
    """构建菜单管理树形结构（用于管理端树展示）。

    Args:
        nodes (list[Menu]): 菜单查询集。

    Returns:
        list[dict[str, Any]]: 菜单树节点列表（含 children）。
    """
    by_parent: dict[int, list[Menu]] = {}
    for m in nodes:
        pid = m.parent_id or 0
        by_parent.setdefault(pid, []).append(m)

    def build(pid: int | None = None) -> list[dict[str, Any]]:
        """递归构建菜单树。"""
        res = []
        for m in by_parent.get(pid or 0, []):
            item = {
                "id": m.id,
                "parentId": m.parent_id,
                "name": m.name,
                "type": m.type,
                "path": m.path,
                "component": m.component,
                "perms": m.perms,
                "icon": m.icon,
                "sort": m.order_num,
                "visible": 1 if m.visible else 0,
                "status": 1 if m.status else 0,
                "routeName": m.route_name or "",
            }
            children = build(m.id)
            if children:
                item["children"] = children
            res.append(item)
        return res

    return build(None)


def build_menu_options(nodes: list[Menu]) -> list[dict[str, Any]]:
    """构建菜单下拉选项树（用于岗位分配菜单场景）。

    Args:
        nodes (list[Menu]): 菜单查询集。

    Returns:
        list[dict[str, Any]]: 下拉选项节点列表（value/label/children）。
    """
    by_parent: dict[int, list[Menu]] = {}
    for m in nodes:
        pid = m.parent_id or 0
        by_parent.setdefault(pid, []).append(m)

    def build(pid: int | None = None) -> list[dict[str, Any]]:
        """递归构建下拉选项树。"""
        res = []
        for m in by_parent.get(pid or 0, []):
            item = {"value": m.id, "label": m.name}
            children = build(m.id)
            if children:
                item["children"] = children
            res.append(item)
        return res

    return build(None)
