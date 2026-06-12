"""SP 广告视图子包。"""
from api_v1.views.lingxing.ads.sp.ad_campaign_view import AdCampaignViewSet
from api_v1.views.lingxing.ads.sp.ad_group_view import AdGroupViewSet
from api_v1.views.lingxing.ads.sp.ad_view import AdViewSet
from api_v1.views.lingxing.ads.sp.auto_targeting_view import AutoTargetingViewSet
from api_v1.views.lingxing.ads.sp.keyword_view import KeywordViewSet
from api_v1.views.lingxing.ads.sp.auto_negative_targeting_view import AutoNegativeTargetingViewSet
from api_v1.views.lingxing.ads.sp.negative_keyword_view import NegativeKeywordViewSet
from api_v1.views.lingxing.ads.sp.time_pricing_strategy_view import TimePricingStrategyViewSet
from api_v1.views.lingxing.ads.sp.rule_strategy_view import RuleStrategyViewSet, RuleStrategyGroupViewSet

__all__ = [
    "AdCampaignViewSet",
    "AdGroupViewSet",
    "AdViewSet",
    "AutoTargetingViewSet",
    "KeywordViewSet",
    "AutoNegativeTargetingViewSet",
    "NegativeKeywordViewSet",
    "TimePricingStrategyViewSet",
    "RuleStrategyViewSet",
    "RuleStrategyGroupViewSet",
]
