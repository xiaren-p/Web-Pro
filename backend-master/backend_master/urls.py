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
    # 任务调度接口（v2）：工作流执行引擎，文件转换、AI 工作流等异步任务
    path('api/v2/', include('api_v2.urls')),
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
            re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        ]
