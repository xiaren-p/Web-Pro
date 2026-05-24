"""
URL configuration for backend_master project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve

from api_v1.views.oidc.oidc_login_view import oidc_login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # OIDC SSO 登录页：oauth2_provider 未登录时重定向至此（settings.LOGIN_URL 默认值）
    path('accounts/login/', oidc_login_view, name='login'),
    # OIDC Provider 端点（/o/authorize/, /o/token/, /o/userinfo/, /o/.well-known/...）
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    # 业务接口入口（v1）：所有系统管理与认证相关的接口都在此下方
    path('api/v1/', include('api_v1.urls')),
    # 兼容前端在构建时使用 `/prod-api` 前缀的部署方式：
    # 将 /prod-api/... 映射到相同的 api_v1 路由集合，避免 nginx 配置不一致时 404
    path('prod-api/', include('api_v1.urls')),
    # 兼容旧的直接访问路径：将部分根路径请求重定向到 api/v1 下的相应接口
    path('crawler/logs', RedirectView.as_view(url='/api/v1/crawler/logs', permanent=False)),
]

# 媒体文件服务（开发环境）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    if getattr(settings, "DJANGO_SERVE_MEDIA", True):
        urlpatterns += [
            # nginx 通常只反代 /api/ 和 /prod-api/ 到 Django，不反代 /media/。
            # 因此头像等媒体文件统一走 /api/v1/media/ 路径，与业务接口共用同一反代规则，
            # 无需额外修改 nginx 配置即可在生产环境访问。
            re_path(r'^api/v1/media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
            re_path(r'^prod-api/media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
            # 保留原始 /media/ 路径兼容旧数据库记录（如 nginx 已有 location /media/ 则由 nginx 直接服务）
            re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        ]
