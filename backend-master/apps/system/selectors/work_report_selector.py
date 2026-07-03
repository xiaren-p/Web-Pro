"""工作汇报查询选择器。

提供可见用户范围计算与团队统计聚合的只读逻辑。
"""
import datetime

from django.contrib.auth.models import User
from django.db.models import Count, Q

from apps.system.models import Department
from apps.common.models import WorkReport
from apps.system.models.user_profile import AdminLevel


def get_visible_users(user) -> User.objects:
    """根据当前用户的 admin_level 返回可见用户 QuerySet。

    Args:
        user: Django User 实例。

    Returns:
        User QuerySet: 已按权限范围筛选并 select_related profile。
    """
    profile = getattr(user, "profile", None)
    level = profile.admin_level if profile else AdminLevel.MEMBER

    if user.is_superuser or level == AdminLevel.COMPANY_ADMIN:
        return User.objects.filter(is_active=True).select_related("profile__dept")

    if level == AdminLevel.DEPT_ADMIN and profile and profile.dept_id:
        dept_ids = _collect_dept_ids(profile.dept_id)
        return User.objects.filter(
            profile__dept_id__in=list(dept_ids), is_active=True,
        ).select_related("profile__dept")

    return User.objects.filter(id=user.id).select_related("profile__dept")


def _collect_dept_ids(did: int) -> set[int]:
    """递归收集部门及其所有子部门 ID。"""
    dept_ids: set[int] = set()

    def _collect(current_id: int) -> None:
        if current_id in dept_ids:
            return
        dept_ids.add(current_id)
        for cid in Department.objects.filter(parent_id=current_id).values_list("id", flat=True):
            _collect(cid)

    _collect(did)
    return dept_ids


def get_team_stats(user, dept_id: int | None = None, date_str: str | None = None) -> dict:
    """获取团队日报提交统计。

    Args:
        user: Django User 实例。
        dept_id: 可选部门 ID 过滤。
        date_str: 日期字符串 YYYY-MM-DD，默认今天。

    Returns:
        dict: 含 total / submitted / unsubmitted 等字段。
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    target_users = get_visible_users(user)

    if dept_id:
        target_users = target_users.filter(profile__dept_id=dept_id)

    total_count = target_users.count()
    submitted_user_ids = set(
        WorkReport.objects.filter(
            report_date=date_str, user__in=target_users,
        ).values_list("user_id", flat=True)
    )
    submitted_count = len(submitted_user_ids)

    return {
        "total": total_count,
        "submitted": submitted_count,
        "unsubmitted": total_count - submitted_count,
        "date": date_str,
    }


def get_team_stats_details(user, dept_id: int | None = None, dept_name_q: str | None = None,
                           status: str | None = None, date_str: str | None = None) -> list[dict]:
    """获取团队日报提交/未提交详情列表。

    Args:
        user: Django User 实例。
        dept_id: 可选部门 ID。
        dept_name_q: 部门名搜索。
        status: "submitted" | "unsubmitted" 过滤。
        date_str: 日期字符串。

    Returns:
        list[dict]: 用户提交状态列表。
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    target_users = get_visible_users(user)

    if dept_id:
        target_users = target_users.filter(profile__dept_id=dept_id)
    if dept_name_q:
        target_users = target_users.filter(profile__dept__name__icontains=dept_name_q)

    submitted_qs = WorkReport.objects.filter(
        report_date=date_str, user__in=target_users,
    )
    submitted_user_ids = set(submitted_qs.values_list("user_id", flat=True))

    if status == "submitted":
        final_users = target_users.filter(id__in=submitted_user_ids)
    elif status == "unsubmitted":
        final_users = target_users.exclude(id__in=submitted_user_ids)
    else:
        final_users = target_users

    reports = {
        r.user_id: r for r in WorkReport.objects.filter(
            report_date=date_str, user__in=final_users,
        ).only("id", "user_id", "content", "hours")
    }

    result = []
    for u in final_users:
        dept_obj = getattr(getattr(u, "profile", None), "dept", None)
        report = reports.get(u.id)
        result.append({
            "userId": u.id,
            "username": u.username,
            "nickname": getattr(getattr(u, "profile", None), "nickname", "") or u.username,
            "deptName": dept_obj.name if dept_obj else "",
            "submitted": u.id in submitted_user_ids,
            "reportId": report.id if report else None,
            "content": report.content if report else None,
            "hours": report.hours if report else None,
        })

    return result
