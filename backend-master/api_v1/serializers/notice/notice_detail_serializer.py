"""通知公告详情序列化器（含正文与目标用户）。"""
from rest_framework import serializers
from api_v1.models import Notice
from api_v1.serializers.notice.notice_brief_serializer import NoticeBriefSerializer


class NoticeDetailSerializer(NoticeBriefSerializer):
    """通知公告详情序列化器，扩展 brief，增加 content 与 targetUserIds。"""

    targetUserIds = serializers.SerializerMethodField()

    def get_targetUserIds(self, obj: Notice):
        return list(obj.targets.values_list("user_id", flat=True))

    class Meta(NoticeBriefSerializer.Meta):
        fields = NoticeBriefSerializer.Meta.fields + ["content", "targetUserIds"]
