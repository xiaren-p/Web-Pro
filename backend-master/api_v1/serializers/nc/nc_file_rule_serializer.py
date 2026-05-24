"""NC 文件访问规则序列化器（nc_file_access_rule）。"""
from django.conf import settings
from rest_framework import serializers

from api_v1.models.nc.nc_file_access_rule import NcFileAccessRule


def _build_avatar_url(avatar: str) -> str:
    """将 UserProfile.avatar 字段转换为前端可直接使用的完整 URL。

    Args:
        avatar (str): UserProfile.avatar 原始值，可能是 preset:XX、上传路径或空串。

    Returns:
        str: 完整 URL（含 BACKEND_EXTERNAL_URL 前缀），或原始 preset 字符串，或空串。
    """
    if not avatar:
        return ""
    if avatar.startswith("preset:"):
        # preset 类型：原样返回，前端通过 resolveAvatarSrc 转为 SVG data URI 渲染
        return avatar
    if avatar.startswith(("http://", "https://")):
        return avatar
    base = settings.MEDIA_URL.rstrip("/")
    if avatar.startswith("/media/"):
        rel = avatar
    elif avatar.startswith("media/"):
        rel = "/" + avatar
    elif avatar.startswith("uploads/"):
        rel = base + "/" + avatar
    else:
        rel = avatar if avatar.startswith("/") else "/" + avatar
    external = (getattr(settings, "BACKEND_EXTERNAL_URL", "") or "").rstrip("/")
    return external + rel if external else rel


class NcFileRuleReadSerializer(serializers.ModelSerializer):
    """NC 文件访问规则读序列化器：包含用户信息与权限标签。

    所有字段名使用 camelCase，与前端约定对齐。
    """

    userId = serializers.IntegerField(
        source="user_id",
        read_only=True,
    )

    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    userNickname = serializers.SerializerMethodField()

    deptName = serializers.SerializerMethodField()

    ncPath = serializers.CharField(
        source="nc_path",
        read_only=True,
    )

    permissionBits = serializers.IntegerField(
        source="permission_bits",
        read_only=True,
    )

    permLabels = serializers.SerializerMethodField()

    createTime = serializers.DateTimeField(
        source="created_at",
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
    )

    updateTime = serializers.DateTimeField(
        source="updated_at",
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
    )

    avatarUrl = serializers.SerializerMethodField()

    class Meta:
        model = NcFileAccessRule
        fields = [
            "id",
            "userId",
            "username",
            "userNickname",
            "deptName",
            "avatarUrl",
            "ncPath",
            "permissionBits",
            "permLabels",
            "status",
            "createTime",
            "updateTime",
        ]

    def get_userNickname(self, obj: NcFileAccessRule) -> str:
        """从关联的 UserProfile 取昵称，无则回退到 username。

        Returns:
            str: 用户昵称。
        """
        profile = getattr(obj.user, "profile", None)
        return profile.nickname if profile and profile.nickname else obj.user.username

    def get_deptName(self, obj: NcFileAccessRule) -> str:
        """从关联的 UserProfile.dept 取部门名，无则返回空串。

        Returns:
            str: 部门名称。
        """
        profile = getattr(obj.user, "profile", None)
        if profile and profile.dept:
            return profile.dept.name
        return ""

    def get_avatarUrl(self, obj: NcFileAccessRule) -> str:
        """从关联 UserProfile.avatar 构建完整头像 URL，无头像时返回空串。

        Returns:
            str: 完整 URL 或 preset:XX 字符串（前端按后者使用 avatarColor 回退）。
        """
        profile = getattr(obj.user, "profile", None)
        return _build_avatar_url(profile.avatar if profile and profile.avatar else "")

    def get_permLabels(self, obj: NcFileAccessRule) -> list[str]:
        """将 permission_bits 位图解析为可读权限标签列表。

        Returns:
            list[str]: 例如 ["READ", "WRITE", "CREATE"]。
        """
        bits = obj.permission_bits
        labels: list[str] = []
        mapping = [
            (NcFileAccessRule.PERM_READ, "READ"),
            (NcFileAccessRule.PERM_WRITE, "WRITE"),
            (NcFileAccessRule.PERM_CREATE, "CREATE"),
            (NcFileAccessRule.PERM_DELETE, "DELETE"),
            (NcFileAccessRule.PERM_SHARE, "SHARE"),
        ]
        for bit, label in mapping:
            if bits & bit:
                labels.append(label)
        return labels

    def validate_permissionBits(self, value: int) -> int:
        """确保权限位为 1-31 之间的有效位图值。

        Args:
            value (int): 权限位整数。

        Returns:
            int: 验证通过的权限位。

        Raises:
            serializers.ValidationError: 权限位超出有效范围。
        """
        if not (1 <= value <= 31):
            raise serializers.ValidationError("permissionBits 必须在 1~31 之间")
        return value
