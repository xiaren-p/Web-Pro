"""api_v1 权限类包。

按"一类一文件"规则拆分各权限类，本 ``__init__`` 统一重导出，
保证 ``from api_v1.permissions import MenuPermRequired`` 仍然可用。
"""
from api_v1.permissions.menu_perm_required import MenuPermRequired

__all__ = ["MenuPermRequired"]
