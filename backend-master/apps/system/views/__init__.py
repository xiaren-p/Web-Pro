from apps.system.views.app_view import create_app, delete_app, list_apps, rotate_secret
from apps.system.views.auth_view import AuthViewSet
from apps.system.views.codegen_view import CodegenViewSet
from apps.system.views.work_report_view import WorkReportViewSet
from apps.system.views.user_view import UserViewSet
from apps.system.views.profile_view import ProfileViewSet
from apps.system.views.config_view import ConfigViewSet
from apps.system.views.dept_view import DeptViewSet
from apps.system.views.dict_view import DictViewSet
from apps.system.views.log_view import LogViewSet
from apps.system.views.menu_view import MenuViewSet
from apps.system.views.position_view import PositionViewSet
from apps.system.views.oidc_login_view import oidc_login_view

__all__ = [
    "create_app", "delete_app", "list_apps", "rotate_secret",
    "AuthViewSet",
    "CodegenViewSet",
    "WorkReportViewSet",
    "UserViewSet",
    "ProfileViewSet",
    "ConfigViewSet",
    "DeptViewSet",
    "DictViewSet",
    "LogViewSet",
    "MenuViewSet",
    "PositionViewSet",
    "oidc_login_view",
]
