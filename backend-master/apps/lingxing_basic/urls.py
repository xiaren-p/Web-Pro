"""领星基础数据域 — URL 路由。"""
from django.urls import path

from apps.lingxing_basic.views.shop_view import ShopOptionsViewSet

urlpatterns = [
    path("shops/options", ShopOptionsViewSet.as_view({"get": "shops"}), name="shops-options"),
    path("shops/owners", ShopOptionsViewSet.as_view({"get": "owners"}), name="shops-owners"),
]
