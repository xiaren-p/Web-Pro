"""api_v1.views.nc 板块视图包。

NC 权限规则管理视图：NcFolderTreeViewSet、NcDeptGroupViewSet
"""
from api_v1.views.nc.nc_folder_tree_view import NcFolderTreeViewSet
from api_v1.views.nc.nc_dept_group_view import NcDeptGroupViewSet

__all__ = ["NcFolderTreeViewSet", "NcDeptGroupViewSet"]
