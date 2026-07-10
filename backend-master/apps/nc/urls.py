"""Nextcloud 集成域 — URL 路由。

所有路径以 ``api/v1/nc/`` 为前缀（由 ``backend_master/urls.py`` 的 include 提供）。
"""
from django.urls import path, re_path

from apps.nc.views.nc_folder_tree_view import NcFolderTreeViewSet

urlpatterns = [
    path("folder-tree/groups", NcFolderTreeViewSet.as_view({"get": "group_list"}), name="nc-folder-tree-groups"),
    path("folder-tree/list", NcFolderTreeViewSet.as_view({"get": "list_folder"}), name="nc-folder-tree-list"),
    path("folder-tree/mkdir", NcFolderTreeViewSet.as_view({"post": "mkdir"}), name="nc-folder-tree-mkdir"),
    path("folder-tree/folder-delete-preview", NcFolderTreeViewSet.as_view({"get": "folder_delete_preview"}), name="nc-folder-tree-folder-delete-preview"),
    path("folder-tree/folder", NcFolderTreeViewSet.as_view({"delete": "delete_folder"}), name="nc-folder-tree-delete-folder"),
    path("folder-tree/set-rule", NcFolderTreeViewSet.as_view({"post": "set_rule"}), name="nc-folder-tree-set-rule"),
    path("folder-tree/set-rules-batch", NcFolderTreeViewSet.as_view({"post": "set_rules_batch"}), name="nc-folder-tree-set-rules-batch"),
    re_path(r"^folder-tree/rule/(?P<pk>\d+)$", NcFolderTreeViewSet.as_view({"delete": "delete_rule"}), name="nc-folder-tree-delete-rule"),
    path("folder-tree/path-rules", NcFolderTreeViewSet.as_view({"get": "path_rules"}), name="nc-folder-tree-path-rules"),
    path("folder-tree/user-tree", NcFolderTreeViewSet.as_view({"get": "user_tree"}), name="nc-folder-tree-user-tree"),
]
