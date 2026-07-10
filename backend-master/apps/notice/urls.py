"""通知公告域 — URL 路由。

所有路径以 ``api/v1/notices/`` 为前缀（由 ``backend_master/urls.py`` 的 include 提供）。
"""
from django.urls import path

from apps.notice.views.notice_view import NoticeViewSet

urlpatterns = [
    path("page", NoticeViewSet.as_view({"get": "page"}), name="notices-page"),
    path("<str:id>/form", NoticeViewSet.as_view({"get": "form"}), name="notice-form"),
    path("<str:id>/publish", NoticeViewSet.as_view({"post": "publish"}), name="notice-publish"),
    path("<str:id>/revoke", NoticeViewSet.as_view({"post": "revoke"}), name="notice-revoke"),
    path("<str:id>/read", NoticeViewSet.as_view({"post": "read"}), name="notice-read"),
    path("<str:id>/detail", NoticeViewSet.as_view({"get": "detail_plain"}), name="notice-detail"),
    path("read-all", NoticeViewSet.as_view({"post": "read_all"}), name="notice-read-all"),
    path("my-page", NoticeViewSet.as_view({"get": "my_page"}), name="notices-my-page"),
    path("export", NoticeViewSet.as_view({"get": "export_data"}), name="notices-export"),
    path("", NoticeViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="notices-list-create"),
    path("<str:ids>", NoticeViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="notice-update-delete"),
]
