"""工作汇报视图集。

权限体系：基于 admin_level（管理级别）决定可见数据范围。
    COMPANY_ADMIN → 全部数据
    DEPT_ADMIN    → 本部门及所有子部门
    MEMBER        → 仅本人
"""

from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User

from api_v1.models import WorkReport, Department
from api_v1.models.system.user_profile import AdminLevel
from api_v1.serializers import WorkReportSerializer
from django.utils import timezone
from api_v1.utils.pagination import StandardPagination


def _get_target_users(user) -> "User.objects":
    """根据当前用户的 admin_level 返回可见用户集合。

    Args:
        user: Django User 实例，需关联 profile。

    Returns:
        Django User QuerySet，已按权限范围筛选。
    """
    profile = getattr(user, "profile", None)
    level = profile.admin_level if profile else AdminLevel.MEMBER

    if user.is_superuser or level == AdminLevel.COMPANY_ADMIN:
        return User.objects.filter(is_active=True)
    elif level == AdminLevel.DEPT_ADMIN and profile and profile.dept_id:
        dept_ids: set[int] = set()

        def _collect(did: int) -> None:
            if did in dept_ids:
                return
            dept_ids.add(did)
            for cid in Department.objects.filter(parent_id=did).values_list("id", flat=True):
                _collect(cid)

        _collect(profile.dept_id)
        return User.objects.filter(profile__dept_id__in=list(dept_ids), is_active=True)
    else:
        return User.objects.filter(id=user.id)


class WorkReportViewSet(viewsets.ModelViewSet):
    """工作汇报视图集。

    支持 scope=my（默认）和 scope=team 查询参数。
    支持 department（部门名称）模糊查询。
    """

    queryset = WorkReport.objects.all()
    serializer_class = WorkReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["type", "report_date"]
    search_fields = ["content", "plan", "issues", "user__username", "user__profile__nickname"]
    ordering_fields = ["report_date", "created_at"]

    def perform_create(self, serializer) -> None:
        """保存时自动绑定当前用户。"""
        serializer.save(user=self.request.user)

    def get_queryset(self):
        """根据 scope 与 admin_level 返回合法的工作汇报集合。"""
        user = self.request.user
        scope = self.request.query_params.get("scope", "my")

        if scope == "my":
            qs = WorkReport.objects.filter(user=user)
        elif scope == "team":
            target_users = _get_target_users(user)
            qs = WorkReport.objects.filter(user__in=target_users)
        else:
            qs = WorkReport.objects.filter(user=user)

        dept_id = self.request.query_params.get("dept_id")
        if dept_id:
            qs = qs.filter(user__profile__dept_id=dept_id)

        dept_name = self.request.query_params.get("department")
        if dept_name and not dept_id:
            qs = qs.filter(user__profile__dept__name__icontains=dept_name)

        return qs

    @action(detail=False, methods=["get"])
    def team_stats(self, request) -> Response:
        """按日期统计团队汇报提交情况。"""
        user = request.user
        date_str = request.query_params.get("date") or timezone.now().strftime("%Y-%m-%d")

        target_users = _get_target_users(user)

        dept_id = request.query_params.get("dept_id")
        dept_name_q = request.query_params.get("department")
        report_type = request.query_params.get("type")

        if dept_id:
            target_users = target_users.filter(profile__dept_id=dept_id)
        elif dept_name_q:
            target_users = target_users.filter(profile__dept__name__icontains=dept_name_q)

        total_count = target_users.count()
        submitted_qs = WorkReport.objects.filter(report_date=date_str, user__in=target_users)
        if report_type:
            submitted_qs = submitted_qs.filter(type=report_type)

        submitted_count = submitted_qs.values("user").distinct().count()
        missing_count = total_count - submitted_count

        return Response({
            "total": total_count,
            "submitted": submitted_count,
            "missing": missing_count,
        })

    @action(detail=False, methods=["get"])
    def team_stats_details(self, request) -> Response:
        """按日期返回团队成员汇报详情列表。"""
        user = request.user
        date_str = request.query_params.get("date") or timezone.now().strftime("%Y-%m-%d")

        target_users = _get_target_users(user)

        dept_id = request.query_params.get("dept_id")
        dept_name_q = request.query_params.get("department")
        if dept_id:
            target_users = target_users.filter(profile__dept_id=dept_id)
        elif dept_name_q:
            target_users = target_users.filter(profile__dept__name__icontains=dept_name_q)

        status = request.query_params.get("status", "total")
        report_type = request.query_params.get("type")

        submitted_qs = WorkReport.objects.filter(report_date=date_str)
        if report_type:
            submitted_qs = submitted_qs.filter(type=report_type)

        submitted_user_ids = submitted_qs.values_list("user_id", flat=True)

        final_users = target_users
        if status == "submitted":
            final_users = target_users.filter(id__in=submitted_user_ids)
        elif status == "missing":
            final_users = target_users.exclude(id__in=submitted_user_ids)

        data = []
        for u in final_users:
            dept_obj = getattr(getattr(u, "profile", None), "dept", None)
            data.append({
                "id": u.id,
                "username": u.username,
                "nickname": getattr(getattr(u, "profile", None), "nickname", ""),
                "avatar": getattr(getattr(u, "profile", None), "avatar", ""),
                "department": dept_obj.name if dept_obj else "",
            })
        return Response(data)
