"""通知公告通用序列化器（与 detail 行为一致，作为默认导出别名）。"""
from api_v1.serializers.notice.notice_detail_serializer import NoticeDetailSerializer


class NoticeSerializer(NoticeDetailSerializer):
    """通知公告默认序列化器（继承 detail，无额外行为）。"""

    pass
