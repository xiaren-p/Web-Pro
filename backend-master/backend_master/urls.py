"""
URL configuration for backend_master project.

路由设计原则：
- 所有业务域的路由委托到各自 ``apps/<域>/urls.py`` 管理
- ``api/v1/`` 前缀由 include 提供，域 urls.py 只写相对路径
- 非域路由（admin / oauth / 重定向 / API 根）保留在此文件
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from apps.system.views.oidc_login_view import oidc_login_view
from apps.common.utils.responses import drf_ok


def api_root(request):
    return drf_ok({"name": "backend_master"})


urlpatterns = [
    # ═══════════════════════════════════════════════════════════════
    # 非域路由（不归属任何业务域）
    # ═══════════════════════════════════════════════════════════════
    path("admin/", admin.site.urls),
    path("accounts/login/", oidc_login_view, name="login"),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),

    # ═══════════════════════════════════════════════════════════════
    # 系统管理域 — auth / 用户 / 岗位 / 菜单 / 日志 / 字典 / 部门 / 配置 / 工作汇报
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/", include("apps.system.urls")),

    # ═══════════════════════════════════════════════════════════════
    # 广告域 — 活动 / 关键词 / 定位 / 策略 / 规则
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/", include("apps.ads.urls")),

    # 广告子域 — 分时调价触发 / 上传队列 / 竞价调整（独立路由模块，非 ads/urls.py 子集）
    path("api/v1/", include("apps.ads.sp.timing.urls")),
    path("api/v1/", include("apps.ads.sp.rules.urls")),

    # ═══════════════════════════════════════════════════════════════
    # 销售域 — Listing / 标签 / 图片上传
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/", include("apps.sales.urls")),

    # ═══════════════════════════════════════════════════════════════
    # 领星基础数据域 — 店铺下拉
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/", include("apps.lingxing_basic.urls")),

    # ═══════════════════════════════════════════════════════════════
    # 通知公告域
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/notices/", include("apps.notice.urls")),

    # ═══════════════════════════════════════════════════════════════
    # Nextcloud 集成域
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/nc/", include("apps.nc.urls")),

    # ═══════════════════════════════════════════════════════════════
    # 爬虫域
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/crawler/", include("apps.crawler.urls")),

    # ═══════════════════════════════════════════════════════════════
    # 通用基础服务域
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/common/", include("apps.common.urls")),

    # ═══════════════════════════════════════════════════════════════
    # AI 助手域
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/ai/", include("apps.ai.urls")),

    # ═══════════════════════════════════════════════════════════════
    # 旧路径重定向
    # ═══════════════════════════════════════════════════════════════
    path("crawler/logs", RedirectView.as_view(url="/api/v1/crawler/logs", permanent=False)),

    # ═══════════════════════════════════════════════════════════════
    # API 根
    # ═══════════════════════════════════════════════════════════════
    path("api/v1/", api_root, name="api-root"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    if getattr(settings, "DJANGO_SERVE_MEDIA", True):
        urlpatterns += [
            re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
        ]
