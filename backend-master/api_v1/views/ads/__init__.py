"""api_v1.views.ads 板块视图包。

按"一类一文件"拆分广告活动相关 ViewSet，重导出以保证旧的
``from api_v1.views.ads_views import XxxViewSet`` 调用路径仍然可用。
"""
from api_v1.views.ads.shop_profile_view import ShopProfileViewSet
from api_v1.views.ads.ad_portfolio_view import AdPortfolioViewSet
from api_v1.views.ads.ad_campaign_view import AdCampaignViewSet
from api_v1.views.ads.ad_group_view import AdGroupViewSet

__all__ = [
    "ShopProfileViewSet",
    "AdPortfolioViewSet",
    "AdCampaignViewSet",
    "AdGroupViewSet",
]
