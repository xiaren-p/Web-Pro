"""系统管理域 — URL 路由。"""

from django.urls import path

from apps.system.views import create_app, delete_app, list_apps, rotate_secret

urlpatterns = [
    path('developer/apps/', list_apps, name='developer_apps_list'),
    path('developer/apps/create/', create_app, name='developer_apps_create'),
    path('developer/apps/<int:app_id>/', delete_app, name='developer_apps_delete'),
    path('developer/apps/<int:app_id>/rotate-secret/', rotate_secret, name='developer_apps_rotate'),
]
