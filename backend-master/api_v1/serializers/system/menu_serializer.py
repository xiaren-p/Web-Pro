"""菜单序列化器。"""
from rest_framework import serializers
from api_v1.models import Menu


class MenuSerializer(serializers.ModelSerializer):
    """菜单读写序列化器。"""

    parentId = serializers.IntegerField(source="parent_id", allow_null=True, required=False)
    sort = serializers.IntegerField(source="order_num", required=False)
    visible = serializers.IntegerField(source="visible", required=False)
    status = serializers.IntegerField(source="status", required=False)
    routeName = serializers.CharField(source="route_name", required=False, allow_blank=True)

    class Meta:
        model = Menu
        fields = [
            "id", "name", "type", "routeName", "path", "component", "perms", "icon",
            "parentId", "sort", "visible", "status",
        ]
