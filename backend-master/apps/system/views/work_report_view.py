"""工作汇报视图集。

权限体系：基于 admin_level（管理级别）决定可见数据范围。
    COMPANY_ADMIN → 全部数据
    DEPT_ADMIN    → 本部门及所有子部门
    MEMBER        → 仅本人
"""
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from apps.common.utils.responses import drf_ok
from rest_framework.decorators import action
from django.utils import timezone

from apps.common.models import WorkReport
from apps.system.serializers import WorkReportSerializer
from apps.common.utils.pagination import StandardPagination
from apps.system.selectors.work_report_selector import get_visible_users, get_team_stats, get_team_stats_details


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
            return WorkReport.objects.filter(user=user)

        target_users = get_visible_users(user)
        qs = WorkReport.objects.filter(user__in=target_users)

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
        result = get_team_stats(
            request.user,
            dept_id=request.query_params.get("dept_id"),
            date_str=request.query_params.get("date"),
        )
        return drf_ok({
            "total": result["total"],
            "submitted": result["submitted"],
            "missing": result["unsubmitted"],
        })

    @action(detail=False, methods=["get"])
    def team_stats_details(self, request) -> Response:
        """按日期返回团队成员汇报详情列表。"""
        data = get_team_stats_details(
            request.user,
            dept_id=request.query_params.get("dept_id"),
            dept_name_q=request.query_params.get("department"),
            status=request.query_params.get("status", "total"),
            date_str=request.query_params.get("date"),
        )
        return drf_ok(data)
