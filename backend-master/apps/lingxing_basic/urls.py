"""领星基础数据域 — URL 路由。"""
from django.urls import path

from apps.lingxing_basic.views.shop_options_view import ShopOptionsViewSet
from apps.lingxing_basic.views.owner_options_view import OwnerOptionsViewSet

urlpatterns = [
    path("shops/options", ShopOptionsViewSet.as_view({"get": "shops"}), name="shops-options"),
    path("shops/owners", OwnerOptionsViewSet.as_view({"get": "owners"}), name="shops-owners"),
]
