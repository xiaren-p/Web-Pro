"""NC 文件访问规则序列化器（nc_file_access_rule）。"""
from rest_framework import serializers

from api_v1.models.nc.nc_file_access_rule import NcFileAccessRule
from api_v1.models.nc.nc_group import NcGroup, NcGroupType


class NcFileRuleReadSerializer(serializers.ModelSerializer):
    """NC 文件访问规则读序列化器：包含群组信息与权限标签。

    所有字段名使用 camelCase，与前端约定对齐。
    """

    ncGroupId = serializers.IntegerField(
        source="nc_group_id",
        read_only=True,
    )

    ncGroupCode = serializers.CharField(
        source="nc_group.code",
        read_only=True,
    )

    ncGroupName = serializers.CharField(
        source="nc_group.name",
        read_only=True,
    )

    ncGroupType = serializers.CharField(
        source="nc_group.group_type",
        read_only=True,
    )

    ncPath = serializers.CharField(
        source="nc_path",
        read_only=True,
    )

    permissionBits = serializers.IntegerField(
        source="permission_bits",
        read_only=True,
    )

    permLabels = serializers.SerializerMethodField()

    isGroupFolder = serializers.BooleanField(
        source="is_group_folder",
        read_only=True,
    )

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

    class Meta:
        model = NcFileAccessRule
        fields = [
            "id",
            "ncGroupId",
            "ncGroupCode",
            "ncGroupName",
            "ncGroupType",
            "ncPath",
            "permissionBits",
            "permLabels",
            "isGroupFolder",
            "status",
            "createTime",
            "updateTime",
        ]

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


class NcFileRuleWriteSerializer(serializers.ModelSerializer):
    """NC 文件访问规则写序列化器：接受 nc_group_id、nc_path、permission_bits、status。"""

    ncGroupId = serializers.PrimaryKeyRelatedField(
        queryset=NcGroup.objects.filter(
            group_type=NcGroupType.DEPT_ADMIN,
        ),
        source="nc_group",
        write_only=True,
    )

    ncPath = serializers.CharField(
        source="nc_path",
        max_length=500,
    )

    permissionBits = serializers.IntegerField(
        source="permission_bits",
        min_value=1,
        max_value=31,
    )

    isGroupFolder = serializers.BooleanField(
        source="is_group_folder",
        required=False,
        default=True,
    )

    class Meta:
        model = NcFileAccessRule
        fields = ["ncGroupId", "ncPath", "permissionBits", "isGroupFolder", "status"]
        extra_kwargs = {
            "status": {"required": False, "default": True},
        }

    def validate_ncPath(self, value: str) -> str:
        """去除路径首尾斜杠，防止重复记录。

        Args:
            value (str): 前端传入的路径字符串。

        Returns:
            str: 清理后的路径字符串。
        """
        return value.strip("/")

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
