"""用户序列化器。"""
from rest_framework import serializers
from django.contrib.auth.models import User

from api_v1.models.system.user_profile import AdminLevel


class UserSerializer(serializers.ModelSerializer):
    """系统用户读取序列化器。

    通过 ``profile`` 关联读取扩展字段，并将后端 snake_case 映射为前端 camelCase。
    """

    nickname = serializers.CharField(source="profile.nickname", allow_blank=True, default="")
    mobile = serializers.CharField(source="profile.mobile", allow_blank=True, default="")
    avatar = serializers.CharField(source="profile.avatar", allow_blank=True, default="")
    deptId = serializers.IntegerField(source="profile.dept_id", allow_null=True, default=None)
    positionId = serializers.SerializerMethodField()
    positionName = serializers.SerializerMethodField()
    adminLevel = serializers.SerializerMethodField()
    adminLevelLabel = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    deptName = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    status_text = serializers.SerializerMethodField()
    createTime = serializers.DateTimeField(source="date_joined", format="%Y-%m-%d %H:%M:%S", read_only=True)

    def get_positionId(self, obj) -> int | None:
        """返回用户岗位 ID。"""
        profile = getattr(obj, "profile", None)
        return profile.position_id if profile else None

    def get_positionName(self, obj) -> str:
        """返回用户岗位名称。"""
        profile = getattr(obj, "profile", None)
        if profile and profile.position_id:
            try:
                return profile.position.name
            except Exception:
                pass
        return ""

    def get_adminLevel(self, obj) -> int:
        """返回管理级别数值。"""
        profile = getattr(obj, "profile", None)
        return profile.admin_level if profile else AdminLevel.MEMBER

    def get_adminLevelLabel(self, obj) -> str:
        """返回管理级别中文标签，前端直接展示。"""
        profile = getattr(obj, "profile", None)
        level = profile.admin_level if profile else AdminLevel.MEMBER
        return AdminLevel(level).label if level in AdminLevel.values else "普通成员"

    def get_gender(self, obj):
        """返回性别数值。"""
        return getattr(getattr(obj, "profile", None), "gender", None)

    def get_deptName(self, obj) -> str:
        """返回所属部门名称。"""
        profile = getattr(obj, "profile", None)
        if profile and profile.dept:
            return profile.dept.name
        return ""

    def get_status(self, obj) -> int:
        """返回账号启用状态（1=启用，0=禁用）。"""
        return 1 if obj.is_active else 0

    def get_status_text(self, obj) -> str:
        """返回账号启用状态中文标签，前端直接展示。"""
        return "正常" if obj.is_active else "禁用"

    class Meta:
        model = User
        fields = [
            "id", "username", "nickname", "mobile", "avatar", "email",
            "deptId", "deptName", "positionId", "positionName",
            "adminLevel", "adminLevelLabel", "gender",
            "status", "status_text", "createTime",
        ]
