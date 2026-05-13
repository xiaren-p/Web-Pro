"""通知公告简要序列化器（列表场景）。"""
from rest_framework import serializers
from api_v1.models import Notice


class NoticeBriefSerializer(serializers.ModelSerializer):
    """通知公告列表简要信息序列化器（前端 camelCase 字段适配）。"""

    publishStatus = serializers.SerializerMethodField()
    publisherName = serializers.SerializerMethodField()
    publishTime = serializers.SerializerMethodField()
    revokeTime = serializers.SerializerMethodField()
    createTime = serializers.DateTimeField(source="created_at", format="%Y-%m-%d %H:%M:%S", read_only=True)
    targetType = serializers.IntegerField(source="target_type", default=1)

    def get_publishStatus(self, obj: Notice):
        # 0=未发布, 1=已发布, -1=已撤回
        return 1 if obj.status == "published" else (-1 if obj.status == "revoked" else 0)

    def get_publisherName(self, obj: Notice):
        return getattr(obj.creator, "username", "")

    def get_publishTime(self, obj: Notice):
        return obj.publish_time.strftime("%Y-%m-%d %H:%M:%S") if obj.publish_time else None

    def get_revokeTime(self, obj: Notice):
        return obj.revoke_time.strftime("%Y-%m-%d %H:%M:%S") if obj.revoke_time else None

    class Meta:
        model = Notice
        fields = [
            "id", "title", "type", "level", "targetType", "publishStatus",
            "publisherName", "publishTime", "revokeTime", "createTime", "status",
        ]
