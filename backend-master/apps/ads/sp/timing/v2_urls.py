"""分时调价域 — api_v2 路由。"""

from django.urls import path

from apps.ads.sp.timing.views.ad_time_pricing_view import trigger_time_pricing

urlpatterns = [
    path('ads/time-pricing/execute/', trigger_time_pricing, name='ads_time_pricing_execute'),
]
