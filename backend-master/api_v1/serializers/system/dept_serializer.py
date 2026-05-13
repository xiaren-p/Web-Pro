"""部门序列化器。"""
from rest_framework import serializers
from api_v1.models import Department


class DeptSerializer(serializers.ModelSerializer):
    """部门读写序列化器。"""

    parentId = serializers.IntegerField(source="parent_id", allow_null=True, required=False)
    sort = serializers.IntegerField(source="order_num")
    code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Department
        fields = ["id", "name", "code", "status", "parentId", "sort"]
