"""通知公告详情序列化器（含正文与目标用户）。"""
from rest_framework import serializers
from apps.notice.models import Notice
from apps.notice.serializers.notice_brief_serializer import NoticeBriefSerializer


class NoticeDetailSerializer(NoticeBriefSerializer):
    """通知公告详情序列化器，扩展 brief，增加 content 与 targetUserIds。"""

    targetUserIds = serializers.SerializerMethodField()

    def get_targetUserIds(self, obj: Notice):
        """获取 targetUserIds。"""
        return list(obj.targets.values_list("user_id", flat=True))

    class Meta(NoticeBriefSerializer.Meta):
        fields = NoticeBriefSerializer.Meta.fields + ["content", "targetUserIds"]
