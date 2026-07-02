"""爬虫域 — URL 路由。"""

from django.urls import path, re_path

from apps.crawler.views import (
    CrawlerCategoryViewSet,
    CrawlerConfViewSet,
    CrawlerLogViewSet,
    CrawlerSellerViewSet,
)

urlpatterns = [
    # 配置管理
    path("conf", CrawlerConfViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="crawler-conf-list"),
    path("conf/<str:id>/form", CrawlerConfViewSet.as_view({"get": "form"}), name="crawler-conf-form"),
    path("conf/<str:ids>", CrawlerConfViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="crawler-conf-detail"),
    # 账号管理
    path("seller", CrawlerSellerViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="crawler-seller-list"),
    path("seller/<str:id>/form", CrawlerSellerViewSet.as_view({"get": "form"}), name="crawler-seller-form"),
    path("seller/<str:ids>", CrawlerSellerViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="crawler-seller-detail"),
    # 日志
    path("logs/page", CrawlerLogViewSet.as_view({"get": "page"}), name="crawler-logs-page"),
    path("logs", CrawlerLogViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="crawler-logs-list"),
    # 分类
    path("category/page", CrawlerCategoryViewSet.as_view({"get": "page"}), name="crawler-category-page"),
    path("category/sites", CrawlerCategoryViewSet.as_view({"get": "sites"}), name="crawler-category-sites"),
    path("category", CrawlerCategoryViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="crawler-category-list"),
    path("category/<str:id>/form", CrawlerCategoryViewSet.as_view({"get": "form"}), name="crawler-category-form"),
    path("category/<str:ids>", CrawlerCategoryViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="crawler-category-detail"),
]
