"""部门权限范围辅助工具：返回调用方可管辖的部门 ID 集合。"""
from api_v1.models.system.department import Department
from api_v1.models.system.user_profile import AdminLevel


def get_caller_dept_ids(user) -> set[int] | None:
    """返回调用方有权管辖的部门 ID 集合（含自身及所有子部门）。

    Args:
        user: Django 登录用户对象（request.user）。

    Returns:
        None  → 公司管理员 / superuser，不受部门限制。
        set   → DEPT_ADMIN 可管辖的部门 ID（含自身及所有子部门）。
        空集  → 普通成员，无权操作任何资源。
    """
    if getattr(user, "is_superuser", False):
        return None
    profile = getattr(user, "profile", None)
    if profile is None:
        return set()
    level = profile.admin_level
    if level == AdminLevel.COMPANY_ADMIN:
        return None
    if level == AdminLevel.DEPT_ADMIN and profile.dept_id:
        dept_ids: set[int] = set()

        def _collect(did: int) -> None:
            if did in dept_ids:
                return
            dept_ids.add(did)
            for cid in Department.objects.filter(parent_id=did).values_list("id", flat=True):
                _collect(cid)

        _collect(profile.dept_id)
        return dept_ids
    return set()
