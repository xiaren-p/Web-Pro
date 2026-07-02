"""Nextcloud 集成域 — URL 路由。"""

from django.urls import path, re_path

from apps.nc.views import NcFolderTreeViewSet

urlpatterns = [
    path("folder-tree/groups", NcFolderTreeViewSet.as_view({"get": "group_list"}), name="nc-groups"),
    path("folder-tree/list", NcFolderTreeViewSet.as_view({"get": "list_folder"}), name="nc-folder-list"),
    path("folder-tree/mkdir", NcFolderTreeViewSet.as_view({"post": "mkdir"}), name="nc-mkdir"),
    path("folder-tree/folder-delete-preview", NcFolderTreeViewSet.as_view({"get": "folder_delete_preview"}), name="nc-delete-preview"),
    path("folder-tree/folder", NcFolderTreeViewSet.as_view({"delete": "delete_folder"}), name="nc-delete-folder"),
    path("folder-tree/set-rule", NcFolderTreeViewSet.as_view({"post": "set_rule"}), name="nc-set-rule"),
    path("folder-tree/set-rules-batch", NcFolderTreeViewSet.as_view({"post": "set_rules_batch"}), name="nc-set-rules-batch"),
    re_path(r"^folder-tree/rule/(?P<pk>\d+)$", NcFolderTreeViewSet.as_view({"delete": "delete_rule"}), name="nc-delete-rule"),
    path("folder-tree/path-rules", NcFolderTreeViewSet.as_view({"get": "path_rules"}), name="nc-path-rules"),
    path("folder-tree/user-tree", NcFolderTreeViewSet.as_view({"get": "user_tree"}), name="nc-user-tree"),
]
