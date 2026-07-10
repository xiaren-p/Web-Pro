"""系统管理域 — URL 路由。

所有路径以 ``api/v1/`` 为前缀（由 ``backend_master/urls.py`` 的 include 提供）。
"""
from django.urls import path, re_path
from django.views.decorators.csrf import csrf_exempt

from apps.system.views.auth_view import AuthViewSet
from apps.system.views.user_view import UserViewSet
from apps.system.views.profile_view import ProfileViewSet
from apps.system.views.config_view import ConfigViewSet
from apps.system.views.dept_view import DeptViewSet
from apps.system.views.dict_view import DictViewSet
from apps.system.views.log_view import LogViewSet
from apps.system.views.menu_view import MenuViewSet
from apps.system.views.oidc_login_view import oidc_login_view
from apps.system.views.position_view import PositionViewSet
from apps.system.views.codegen_view import CodegenViewSet
from apps.system.views.work_report_view import WorkReportViewSet
from apps.system.views import create_app, delete_app, list_apps, rotate_secret

urlpatterns = [
    # ── 认证 ──
    path("auth/login", AuthViewSet.as_view({"post": "login"}), name="auth-login"),
    path("auth/refresh-token", csrf_exempt(AuthViewSet.as_view({"post": "refresh_token"})), name="auth-refresh"),
    path("auth/logout", AuthViewSet.as_view({"delete": "logout", "get": "logout", "post": "logout"}), name="auth-logout"),
    path("auth/captcha", AuthViewSet.as_view({"get": "captcha"}), name="auth-captcha"),
    path("auth/sso-session", AuthViewSet.as_view({"post": "sso_session"}), name="auth-sso-session"),

    # ── 代码生成 ──
    path("codegen/table/page", CodegenViewSet.as_view({"get": "table_page"}), name="codegen-table-page"),
    path("codegen/<str:table_name>/config", CodegenViewSet.as_view({"get": "config", "post": "config", "delete": "config"}), name="codegen-config"),
    path("codegen/<str:table_name>/preview", CodegenViewSet.as_view({"get": "preview"}), name="codegen-preview"),
    path("codegen/<str:table_name>/download", CodegenViewSet.as_view({"get": "download"}), name="codegen-download"),

    # ── 用户 ──
    path("users/me", UserViewSet.as_view({"get": "me"}), name="user-me"),
    path("users/page", UserViewSet.as_view({"get": "page"}), name="user-page"),
    path("users/<str:user_id>/form", UserViewSet.as_view({"get": "form"}), name="user-form"),
    path("users/profile", UserViewSet.as_view({"get": "profile_get", "put": "profile_put"}), name="user-profile"),
    path("users/password", UserViewSet.as_view({"put": "change_password"}), name="user-change-password"),
    path("users/avatar", UserViewSet.as_view({"post": "upload_avatar"}), name="user-upload-avatar"),
    path("users/upload-image", UserViewSet.as_view({"post": "upload_image"}), name="user-upload-image"),
    path("users/options", UserViewSet.as_view({"get": "options"}), name="user-options"),
    path("users", UserViewSet.as_view({"get": "generic_get", "post": "create"}), name="users-create"),
    path("users/<str:id>", UserViewSet.as_view({"put": "update", "delete": "delete"}), name="user-update-delete"),
    path("users/<str:id>/password/reset", UserViewSet.as_view({"put": "reset_password"}), name="user-reset-password"),
    path("users/mobile/code", ProfileViewSet.as_view({"post": "send_mobile_code"}), name="user-mobile-code"),
    path("users/mobile", ProfileViewSet.as_view({"put": "bind_mobile"}), name="user-bind-mobile"),
    path("users/email/code", ProfileViewSet.as_view({"post": "send_email_code"}), name="user-email-code"),
    path("users/email", ProfileViewSet.as_view({"put": "bind_email"}), name="user-bind-email"),

    # ── 岗位 ──
    path("positions/page", PositionViewSet.as_view({"get": "page"}), name="positions-page"),
    path("positions/options", PositionViewSet.as_view({"get": "options"}), name="positions-options"),
    path("positions", PositionViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="positions-list-create"),
    path("positions/<str:position_id>/form", PositionViewSet.as_view({"get": "form"}), name="position-form"),
    path("positions/<str:ids>", PositionViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="position-update-delete"),
    path("positions/<str:position_id>/menuIds", PositionViewSet.as_view({"get": "menu_ids"}), name="position-menu-ids"),
    path("positions/<str:position_id>/menus", PositionViewSet.as_view({"put": "update_menus"}), name="position-update-menus"),

    # ── 菜单 ──
    path("menus/routes", MenuViewSet.as_view({"get": "routes"}), name="menus-routes"),
    path("menus/tree", MenuViewSet.as_view({"get": "tree"}), name="menus-tree"),
    path("menus", MenuViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="menus-list-create"),
    path("menus/options", MenuViewSet.as_view({"get": "options"}), name="menus-options"),
    path("menus/<str:id>/form", MenuViewSet.as_view({"get": "form"}), name="menu-form"),
    path("menus/<str:id>", MenuViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="menu-update-delete"),

    # ── 日志 ──
    path("logs/page", LogViewSet.as_view({"get": "page"}), name="logs-page"),
    path("logs/visit-trend", LogViewSet.as_view({"get": "visit_trend"}), name="logs-visit-trend"),
    path("logs/visit-stats", LogViewSet.as_view({"get": "visit_stats"}), name="logs-visit-stats"),

    # ── 字典 ──
    path("dicts/page", DictViewSet.as_view({"get": "page"}), name="dicts-page"),
    path("dicts", DictViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="dicts-list-create"),
    path("dicts/<str:id>/form", DictViewSet.as_view({"get": "form"}), name="dict-form"),
    path("dicts/<str:ids>", DictViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="dict-update-delete"),
    path("dicts/<str:dict_code>/items", DictViewSet.as_view({"get": "items_list_or_create", "post": "items_list_or_create"}), name="dict-items-list-create"),
    path("dicts/<str:dict_code>/items/page", DictViewSet.as_view({"get": "items_page"}), name="dict-items-page"),
    path("dicts/<str:dict_code>/items/<str:item_id>/form", DictViewSet.as_view({"get": "item_form"}), name="dict-item-form"),
    path("dicts/<str:dict_code>/items/options", DictViewSet.as_view({"get": "item_options"}), name="dict-item-options"),
    path("dicts/<str:dict_code>/items/<str:item_id>", DictViewSet.as_view({"put": "item_update_or_delete", "delete": "item_update_or_delete"}), name="dict-item-update-delete"),

    # ── 部门 ──
    path("depts", DeptViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="depts-list-create"),
    path("depts/tree", DeptViewSet.as_view({"get": "tree"}), name="depts-tree"),
    path("depts/options", DeptViewSet.as_view({"get": "options"}), name="depts-options"),
    path("depts/<str:id>/form", DeptViewSet.as_view({"get": "form"}), name="dept-form"),
    path("depts/<str:ids>", DeptViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="dept-update-delete"),

    # ── 配置 ──
    path("configs/page", ConfigViewSet.as_view({"get": "page"}), name="configs-page"),
    path("configs", ConfigViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="configs-list-create"),
    path("configs/<str:id>/form", ConfigViewSet.as_view({"get": "form"}), name="config-form"),
    path("configs/refresh-cache", ConfigViewSet.as_view({"post": "refresh_cache"}), name="configs-refresh-cache"),
    path("configs/<str:ids>", ConfigViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="config-update-delete"),

    # ── 工作汇报 ──
    path("work-report/team/stats/details", WorkReportViewSet.as_view({"get": "team_stats_details"}), name="work-report-team-stats-details"),
    path("work-report/team/stats", WorkReportViewSet.as_view({"get": "team_stats"}), name="work-report-team-stats"),
    path("work-report", WorkReportViewSet.as_view({"get": "list"}), name="work-report-list"),
    path("work-report/<str:pk>", WorkReportViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="work-report-detail"),

    # ── 开发者应用 ──
    path("developer/apps/", list_apps, name="developer_apps_list"),
    path("developer/apps/create/", create_app, name="developer_apps_create"),
    path("developer/apps/<int:app_id>/", delete_app, name="developer_apps_delete"),
    path("developer/apps/<int:app_id>/rotate-secret/", rotate_secret, name="developer_apps_rotate"),
]
