"""api_v2 路由分发 — 全部已迁移到 apps/ 域。"""

from django.urls import path, include

app_name = 'api_v2'

urlpatterns = [
    # 系统管理（apps/system）
    path('', include('apps.system.urls')),

    # AI 工作流（apps/ai）
    path('', include('apps.ai.urls')),

    # 广告分时调价（apps/ads/sp/timing）
    path('', include('apps.ads.sp.timing.v2_urls')),

    # 广告规则（apps/ads/sp/rules）
    path('', include('apps.ads.sp.rules.v2_urls')),
]
