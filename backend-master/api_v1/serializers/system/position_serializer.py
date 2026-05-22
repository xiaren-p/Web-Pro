"""岗位序列化器（读/写分离）。"""
from rest_framework import serializers

from api_v1.models.system.position import Position


class PositionSerializer(serializers.ModelSerializer):
    """岗位读取序列化器：包含菜单 ID 列表，供前端权限配置页使用。"""

    menuIds = serializers.SerializerMethodField()

    def get_menuIds(self, obj: Position) -> list[int]:
        """返回岗位关联的菜单 ID 列表。

        Args:
            obj (Position): 当前岗位实例。

        Returns:
            list[int]: 菜单 ID 列表。
        """
        return list(obj.menus.values_list("id", flat=True))

    class Meta:
        model = Position
        fields = [
            "id",
            "code",
            "name",
            "status",
            "is_builtin",
            "remark",
            "order_num",
            "menuIds",
        ]


class PositionWriteSerializer(serializers.ModelSerializer):
    """岗位写操作序列化器：支持同步更新关联菜单。"""

    menuIds = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        write_only=True,
    )

    class Meta:
        model = Position
        fields = ["code", "name", "status", "remark", "order_num", "menuIds"]

    def create(self, validated_data: dict) -> Position:
        """新建岗位并关联菜单。

        Args:
            validated_data (dict): 校验后的数据。

        Returns:
            Position: 新建的岗位实例。
        """
        menu_ids: list[int] = validated_data.pop("menuIds", [])
        position = Position.objects.create(**validated_data)
        if menu_ids:
            from api_v1.models.system.menu import Menu
            position.menus.set(Menu.objects.filter(id__in=menu_ids))
        return position

    def update(self, instance: Position, validated_data: dict) -> Position:
        """更新岗位信息及关联菜单。

        Args:
            instance (Position): 待更新的岗位实例。
            validated_data (dict): 校验后的数据。

        Returns:
            Position: 更新后的岗位实例。
        """
        menu_ids: list[int] | None = validated_data.pop("menuIds", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if menu_ids is not None:
            from api_v1.models.system.menu import Menu
            instance.menus.set(Menu.objects.filter(id__in=menu_ids))
        return instance


class PositionOptionSerializer(serializers.ModelSerializer):
    """岗位下拉选项序列化器（轻量）。"""

    class Meta:
        model = Position
        fields = ["id", "code", "name"]
