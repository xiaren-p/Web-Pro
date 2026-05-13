"""基于角色关联菜单 perms 字段的自定义权限类。

使用方式：在 ViewSet 上设置属性 ``required_perms = ['system:role:edit']``。
若用户具备任一菜单的 ``perms`` 包含该字符串（逗号或空格分隔），即放行。

策略说明：
- 超级用户直接放行
- 用户无 profile 或无角色 -> 拒绝
- 汇总角色关联菜单的 perms 字符串集合，匹配 required_perms 中任意一个

未来扩展：
- 缓存用户权限集合（Redis / 本地）
- 支持权限分组与通配符
"""
from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class MenuPermRequired(BasePermission):
    """菜单权限校验类。"""

    message = "无权限"

    def has_permission(self, request: Request, view) -> bool:
        required = getattr(view, "required_perms", None)
        if not required:
            return True  # 未声明权限需求，默认放行
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        # 超级用户直接放行
        if user.is_superuser:
            return True
        # 兼容：若 UserProfile 不存在，访问 user.profile 会抛 DoesNotExist
        try:
            profile = getattr(user, "profile", None)
        except Exception:
            profile = None
        if not profile:
            return False
        try:
            if profile.roles.filter(code="admin").exists():
                return True
        except Exception:
            pass
        # 汇总角色关联菜单 perms
        menus = []
        try:
            for role in profile.roles.all():
                menus.extend(list(role.menus.all()))
        except Exception:
            return False
        perm_values = set()
        for m in menus:
            val = (m.perms or "").strip()
            if not val:
                continue
            # 支持逗号、空格分隔
            for p in [s.strip() for s in val.replace(",", " ").split(" ") if s.strip()]:
                perm_values.add(p)
        # 任意 required 命中即通过
        for r in required:
            if r in perm_values:
                return True
        return False
