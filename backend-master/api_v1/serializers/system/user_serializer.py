"""用户序列化器。"""
from rest_framework import serializers
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """系统用户读取序列化器。

    通过 ``profile`` 关联读取扩展字段，并将后端 snake_case 映射为前端 camelCase。
    """

    nickname = serializers.CharField(source="profile.nickname", allow_blank=True, default="")
    mobile = serializers.CharField(source="profile.mobile", allow_blank=True, default="")
    avatar = serializers.CharField(source="profile.avatar", allow_blank=True, default="")
    cloudId = serializers.CharField(source="profile.cloud_id", allow_blank=True, default="")
    deptId = serializers.IntegerField(source="profile.dept_id", allow_null=True, default=None)
    roleIds = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    deptName = serializers.SerializerMethodField()
    roleNames = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    status_text = serializers.SerializerMethodField()
    createTime = serializers.DateTimeField(source="date_joined", format="%Y-%m-%d %H:%M:%S", read_only=True)

    def get_roleIds(self, obj):
        if hasattr(obj, "profile"):
            return list(obj.profile.roles.values_list("id", flat=True))
        return []

    def get_gender(self, obj):
        return getattr(getattr(obj, "profile", None), "gender", None)

    def get_deptName(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.dept:
            return profile.dept.name
        return ""

    def get_roleNames(self, obj):
        profile = getattr(obj, "profile", None)
        if profile:
            return ",".join(profile.roles.values_list("name", flat=True))
        return ""

    def get_status(self, obj) -> int:
        return 1 if obj.is_active else 0

    def get_status_text(self, obj) -> str:
        """用户启用状态中文标签，前端直接展示。"""
        return "正常" if obj.is_active else "禁用"

    class Meta:
        model = User
        fields = [
            "id", "username", "nickname", "mobile", "avatar", "email",
            "deptId", "deptName", "roleIds", "roleNames", "gender",
            "status", "status_text", "createTime",
            "cloudId",
        ]
