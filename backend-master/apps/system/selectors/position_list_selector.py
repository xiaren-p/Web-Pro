"""岗位列表查询选择器。

提供岗位分页列表与下拉选项的只读查询逻辑。
"""
from django.db.models import Q

from apps.system.models import Position
from apps.system.utils.dept_scope import get_caller_dept_ids


def get_position_page_qs(user, keywords: str | None = None, status_val: str | None = None):
    """构建岗位分页查询集，按 admin_level 过滤部门范围。

    Args:
        user: Django User 实例。
        keywords (str | None): 模糊搜索关键词。
        status_val (str | None): 状态筛选，"0"/"1"。

    Returns:
        Position QuerySet。
    """
    dept_ids = get_caller_dept_ids(user)
    qs = Position.objects.all().order_by("order_num", "id")

    if dept_ids is None:
        pass
    elif dept_ids:
        qs = qs.filter(dept_id__in=dept_ids)
    else:
        qs = qs.none()

    if keywords:
        qs = qs.filter(Q(name__icontains=keywords) | Q(code__icontains=keywords))

    if status_val is not None:
        try:
            qs = qs.filter(status=bool(int(status_val)))
        except (ValueError, TypeError):
            pass

    return qs


def get_position_options_qs(user):
    """构建岗位下拉选项查询集。

    内置岗位（is_builtin=True）不出现。部门管理员仅可见本部门及子部门的岗位。

    Args:
        user: Django User 实例。

    Returns:
        Position QuerySet。
    """
    dept_ids = get_caller_dept_ids(user)
    qs = Position.objects.filter(status=True, is_builtin=False).order_by("order_num", "id")

    if dept_ids is None:
        pass
    elif dept_ids:
        qs = qs.filter(dept_id__in=dept_ids)
    else:
        qs = qs.none()

    return qs
