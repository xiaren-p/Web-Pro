"""基础服务域 — URL 路由。"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.common.views import WeatherViewSet

router = DefaultRouter()
router.register(r"weather", WeatherViewSet, basename="weather")

urlpatterns = [
    path("", include(router.urls)),
]
