from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from api_v1.models import WorkReport, Role, Department
from api_v1.serializers import WorkReportSerializer
from django.utils import timezone
from api_v1.utils.pagination import StandardPagination

class WorkReportViewSet(viewsets.ModelViewSet):
    """
    工作汇报视图集
    支持 'scope=my' (默认) 和 'scope=team' 查询参数。
    支持 'department' (部门名称) 模糊查询。
    """
    queryset = WorkReport.objects.all()
    serializer_class = WorkReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['type', 'report_date']
    search_fields = ['content', 'plan', 'issues', 'user__username', 'user__profile__nickname']
    ordering_fields = ['report_date', 'created_at']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        user = self.request.user
        scope = self.request.query_params.get('scope', 'my')
        
        # Start with None to avoid fetching all if logic fails but usually we set explicit filters
        qs = WorkReport.objects.none()

        if scope == 'my':
            qs = WorkReport.objects.filter(user=user)
        
        elif scope == 'team':
             # 数据权限逻辑
            roles = user.profile.roles.all()
            if not roles.exists():
                qs = WorkReport.objects.filter(user=user)
            else:
                # 1=全部数据, 2=本部门及下级部门, 3=本部门, 4=本人
                min_scopes = [r.data_scope for r in roles]
                min_scope = min(min_scopes) if min_scopes else 4
                
                if min_scope == 1:
                    qs = WorkReport.objects.all()
                elif min_scope == 2:
                    dept = user.profile.dept
                    if dept:
                        # 暂时按本部门
                        qs = WorkReport.objects.filter(user__profile__dept=dept)
                    else:
                        qs = WorkReport.objects.filter(user=user)
                elif min_scope == 3:
                    dept = user.profile.dept
                    if dept:
                        qs = WorkReport.objects.filter(user__profile__dept=dept)
                    else:
                        qs = WorkReport.objects.filter(user=user)
                else:
                    qs = WorkReport.objects.filter(user=user)
        else:
            qs = WorkReport.objects.filter(user=user)

        # 部门筛选
        dept_id = self.request.query_params.get('dept_id')
        if dept_id:
            qs = qs.filter(user__profile__dept_id=dept_id)
        
        # 部门名称筛选 (保留兼容)
        dept_name = self.request.query_params.get('department')
        if dept_name and not dept_id:
            # Note: need access to user -> profile -> dept -> name
            qs = qs.filter(user__profile__dept__name__icontains=dept_name)

        return qs

    @action(detail=False, methods=['get'])
    def team_stats(self, request):
        user = request.user
        date_str = request.query_params.get('date')
        if not date_str:
            date_str = timezone.now().strftime('%Y-%m-%d')
        
        # 简化版权限逻辑 (应提取公共方法)
        roles = user.profile.roles.all()
        min_scope = 4
        if roles.exists():
            min_scope = min([r.data_scope for r in roles])
        
        target_users = User.objects.none()
        if min_scope == 1:
            target_users = User.objects.filter(is_active=True)
        elif min_scope in [2, 3]:
             dept = user.profile.dept
             if dept:
                 target_users = User.objects.filter(profile__dept=dept, is_active=True)
             else:
                 target_users = User.objects.filter(id=user.id)
        else:
             target_users = User.objects.filter(id=user.id)

        # 部门筛选
        dept_id = request.query_params.get('dept_id')
        dept_name = request.query_params.get('department')
        report_type = request.query_params.get('type')
        
        if dept_id and target_users.exists():
            target_users = target_users.filter(profile__dept_id=dept_id)
        elif dept_name and target_users.exists():
            target_users = target_users.filter(profile__dept__name__icontains=dept_name)

        total_count = target_users.count()
        submitted_qs = WorkReport.objects.filter(report_date=date_str, user__in=target_users)
        
        if report_type:
            submitted_qs = submitted_qs.filter(type=report_type)
            
        submitted_count = submitted_qs.values('user').distinct().count()
        missing_count = total_count - submitted_count
        
        return Response({
            'total': total_count,
            'submitted': submitted_count,
            'missing': missing_count
        })

    @action(detail=False, methods=['get'])
    def team_stats_details(self, request):
        user = request.user
        date_str = request.query_params.get('date')
        if not date_str:
             date_str = timezone.now().strftime('%Y-%m-%d')

        roles = user.profile.roles.all()
        min_scope = 4
        if roles.exists():
             min_scope = min([r.data_scope for r in roles])

        target_users = User.objects.none()

        # 1. Determine base target users based on data scope
        if min_scope == 1:
             target_users = User.objects.filter(is_active=True)
        elif min_scope in [2, 3]:
             dept = user.profile.dept
             if dept:
                  target_users = User.objects.filter(profile__dept=dept, is_active=True)
             else:
                  target_users = User.objects.filter(id=user.id)
        else:
             target_users = User.objects.filter(id=user.id)

        # 2. Filter by department if requested
        dept_id = request.query_params.get('dept_id')
        dept_name = request.query_params.get('department')
        if dept_id and target_users.exists():
             target_users = target_users.filter(profile__dept_id=dept_id)
        elif dept_name and target_users.exists():
             target_users = target_users.filter(profile__dept__name__icontains=dept_name)

        # 3. Filter by status (submitted/missing/total)
        status = request.query_params.get('status', 'total')
        report_type = request.query_params.get('type')
        
        submitted_qs = WorkReport.objects.filter(report_date=date_str)
        if report_type:
            submitted_qs = submitted_qs.filter(type=report_type)
            
        submitted_user_ids = submitted_qs.values_list('user_id', flat=True)

        final_users = target_users
        if status == 'submitted':
             final_users = target_users.filter(id__in=submitted_user_ids)
        elif status == 'missing':
             final_users = target_users.exclude(id__in=submitted_user_ids)
        
        # 4. Serialize
        data = []
        for u in final_users:
             dept = getattr(u.profile, 'dept', None)
             dept_name = dept.name if dept else ""
             data.append({
                  "id": u.id,
                  "username": u.username,
                  "nickname": u.profile.nickname,
                  "avatar": u.profile.avatar,
                  "department": dept_name
             })
        return Response(data)
