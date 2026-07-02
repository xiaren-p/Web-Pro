from apps.system.views.auth_view import AuthViewSet
from apps.system.views.user_view import UserViewSet
from apps.system.views.profile_view import ProfileViewSet
from apps.system.views.config_view import ConfigViewSet
from apps.system.views.dept_view import DeptViewSet
from apps.system.views.dict_view import DictViewSet
from apps.system.views.log_view import LogViewSet
from apps.system.views.menu_view import MenuViewSet
from apps.system.views.position_view import PositionViewSet
from apps.system.views.codegen_view import CodegenViewSet
from apps.system.views.work_report_view import WorkReportViewSet
from apps.common.utils.responses import drf_ok

from apps.sales.views.shop_view import ShopOptionsViewSet
from apps.sales.listing.views.listing_view import SalesProductListingViewSet
from apps.sales.listing.views.listing_tag_view import ListingTagViewSet
from apps.sales.listing.views.image_view import ImageUploadViewSet

from apps.ads.views.shop_profile_view import ShopProfileViewSet
from apps.ads.views.ad_portfolio_view import AdPortfolioViewSet
from apps.ads.sp.views.ad_campaign_view import AdCampaignViewSet
from apps.ads.sp.views.ad_group_view import AdGroupViewSet
from apps.ads.sp.views.ad_view import AdViewSet
from apps.ads.sp.views.auto_targeting_view import AutoTargetingViewSet
from apps.ads.sp.views.auto_negative_targeting_view import AutoNegativeTargetingViewSet
from apps.ads.sp.views.keyword_view import KeywordViewSet
from apps.ads.sp.views.negative_keyword_view import NegativeKeywordViewSet
from apps.ads.sp.timing.views.time_pricing_strategy_view import TimePricingStrategyViewSet
from apps.ads.sp.rules.views.rule_strategy_view import RuleStrategyViewSet, RuleStrategyGroupViewSet

from apps.notice.views.notice_view import NoticeViewSet
from apps.nc.views.nc_folder_tree_view import NcFolderTreeViewSet

def root_index(request):
    return drf_ok({"name": "api_v1"})
