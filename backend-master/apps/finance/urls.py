"""财务域 — URL 路由。"""

from django.urls import path

from apps.finance.views.statistics_view import StatisticsViewSet
from apps.finance.views.monthly_loss_view import MonthlyLossViewSet
from apps.finance.views.monthly_loss_first20_view import MonthlyLossFirst20ViewSet

urlpatterns = [
    path("statistics/lossmakingorders_sync", StatisticsViewSet.as_view({"post": "lossmaking_orders_sync"}), name="statistics-lossmaking-orders-sync"),
    path("statistics/lossmakingorders_data", StatisticsViewSet.as_view({"post": "lossmaking_orders_data"}), name="statistics-lossmaking-orders-data"),
    path("statistics/monthly-loss", MonthlyLossViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="monthly-loss-list"),
    path("statistics/monthly-loss/download", MonthlyLossViewSet.as_view({"get": "download", "post": "download"}), name="monthly-loss-download"),
    path("statistics/monthly-loss/<int:id>/form", MonthlyLossViewSet.as_view({"get": "form"}), name="monthly-loss-form"),
    path("statistics/monthly-loss/<str:ids>", MonthlyLossViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="monthly-loss-detail"),
    path("statistics/monthly-loss-first20", MonthlyLossFirst20ViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="monthly-loss-first20-list"),
    path("statistics/monthly-loss-first20/download", MonthlyLossFirst20ViewSet.as_view({"get": "download", "post": "download"}), name="monthly-loss-first20-download"),
    path("statistics/monthly-loss-first20/<int:id>/form", MonthlyLossFirst20ViewSet.as_view({"get": "form"}), name="monthly-loss-first20-form"),
    path("statistics/monthly-loss-first20/<str:ids>", MonthlyLossFirst20ViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="monthly-loss-first20-detail"),
]
