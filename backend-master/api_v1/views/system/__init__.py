"""api_v1.views.system 板块视图包。

按"一类一文件"拆分系统管理（菜单/部门/字典/日志/配置）相关 ViewSet。
重导出以保持旧的 ``from api_v1.views.system_views import XxxViewSet`` 调用路径仍然可用。
"""
from api_v1.views.system.menu_view import MenuViewSet
from api_v1.views.system.dept_view import DeptViewSet
from api_v1.views.system.dict_view import DictViewSet
from api_v1.views.system.log_view import LogViewSet
from api_v1.views.system.config_view import ConfigViewSet
from api_v1.views.system.position_view import PositionViewSet

__all__ = [
    "MenuViewSet",
    "DeptViewSet",
    "DictViewSet",
    "LogViewSet",
    "ConfigViewSet",
    "PositionViewSet",
]
