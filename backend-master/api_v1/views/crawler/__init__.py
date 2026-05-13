"""api_v1.views.crawler 板块视图包。

按"一类一文件"拆分爬虫相关 ViewSet，本 ``__init__`` 重导出，
保证 ``from api_v1.views.crawler_views import XxxViewSet`` 之类的旧调用
通过 ``api_v1.views.__init__`` 的统一入口仍然可用。
"""
from api_v1.views.crawler.crawler_conf_view import CrawlerConfViewSet
from api_v1.views.crawler.crawler_seller_view import CrawlerSellerViewSet
from api_v1.views.crawler.crawler_log_view import CrawlerLogViewSet
from api_v1.views.crawler.crawler_category_view import CrawlerCategoryViewSet

__all__ = [
    "CrawlerConfViewSet",
    "CrawlerSellerViewSet",
    "CrawlerLogViewSet",
    "CrawlerCategoryViewSet",
]
