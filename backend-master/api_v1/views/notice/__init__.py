"""api_v1.views.notice 板块视图包。

通知公告相关 ViewSet，重导出以保持 ``from api_v1.views.notice import NoticeViewSet`` 调用路径不变。
"""
from api_v1.views.notice.notice_view import NoticeViewSet

__all__ = ["NoticeViewSet"]
