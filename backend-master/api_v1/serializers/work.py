"""工作汇报序列化器。"""
from rest_framework import serializers
from api_v1.models import WorkReport


class WorkReportSerializer(serializers.ModelSerializer):
    """工作汇报序列化器。

    额外提供 username / nickname / avatar / department 等只读字段，
    方便前端列表展示，无需二次查询。
    """

    username = serializers.CharField(source="user.username", read_only=True)
    nickname = serializers.CharField(source="user.profile.nickname", read_only=True)
    avatar = serializers.CharField(source="user.profile.avatar", read_only=True)
    department = serializers.CharField(source="user.profile.dept.name", read_only=True)
    # 后端定型字段：前端直接渲染，无需二次转换
    type_display = serializers.SerializerMethodField()
    created_at_display = serializers.SerializerMethodField()

    def get_type_display(self, obj) -> str:
        """汇报类型的中文标签，前端列表/详情直接展示。"""
        mapping = {"daily": "日报", "weekly": "周报", "monthly": "月报"}
        return mapping.get(obj.type, obj.type or "")

    def get_created_at_display(self, obj) -> str:
        """创建时间格式化字符串：``YYYY-MM-DD HH:MM``。"""
        return obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else ""

    class Meta:
        model = WorkReport
        fields = [
            "id", "user", "username", "nickname", "avatar", "department",
            "type", "type_display", "content", "plan", "issues",
            "work_hours", "progress", "report_date",
            "created_at", "created_at_display", "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]
