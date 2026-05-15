from api_v1.views.auth import AuthViewSet
from api_v1.views.user import UserViewSet, ProfileViewSet
from api_v1.views.system import (
    MenuViewSet,
    DeptViewSet,
    DictViewSet,
    LogViewSet,
    ConfigViewSet,
    RoleViewSet,
)
from api_v1.views.notice import NoticeViewSet
from api_v1.views.codegen import CodegenViewSet
from api_v1.views.crawler import (
    CrawlerConfViewSet,
    CrawlerSellerViewSet,
    CrawlerLogViewSet,
    CrawlerCategoryViewSet,
)
from api_v1.views.weather import WeatherViewSet
from api_v1.views.seller import SellerViewSet
from api_v1.views.listing import ImageUploadViewSet, SalesProductListingViewSet
from api_v1.views.finance import StatisticsViewSet, MonthlyLossViewSet, MonthlyLossFirst20ViewSet
from api_v1.utils.responses import drf_ok

def root_index(request):
    return drf_ok({"name": "api_v1"})

from api_v1.views.ads import AdCampaignViewSet, AdPortfolioViewSet, ShopProfileViewSet, AdGroupViewSet, AdViewSet, AutoTargetingViewSet

from api_v1.views.work_report import WorkReportViewSet

