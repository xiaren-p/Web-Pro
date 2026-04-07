from api_v1.views.auth_views import AuthViewSet
from api_v1.views.user_views import UserViewSet, ProfileViewSet
from api_v1.views.role_views import RoleViewSet
from api_v1.views.system_views import MenuViewSet, DeptViewSet, DictViewSet, LogViewSet, ConfigViewSet
from api_v1.views.notice_views import NoticeViewSet
from api_v1.views.codegen_views import CodegenViewSet
from api_v1.views.crawler_views import CrawlerConfViewSet, CrawlerSellerViewSet, CrawlerLogViewSet, CrawlerCategoryViewSet
from api_v1.views.image_views import ImageUploadViewSet
from api_v1.views.weather_views import WeatherViewSet
from api_v1.views.seller_views import SellerViewSet
from api_v1.views.listing_views import SalesProductListingViewSet
from api_v1.views.statistics_views import StatisticsViewSet, MonthlyLossViewSet, MonthlyLossFirst20ViewSet
from api_v1.utils.responses import drf_ok

def root_index(request):
    return drf_ok({"name": "api_v1"})

from .solar_term_views import SolarTermTagViewSet
from .classification_views import ProductClassificationViewSet

from api_v1.views.work_report_views import WorkReportViewSet
