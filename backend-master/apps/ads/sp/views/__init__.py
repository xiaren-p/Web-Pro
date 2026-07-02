"""广告域 — SP 视图层（v1 ViewSet + v2 FBV）。"""
# v1 ViewSets
from apps.ads.sp.views.ad_campaign_view import AdCampaignViewSet
from apps.ads.sp.views.ad_group_view import AdGroupViewSet
from apps.ads.sp.views.ad_view import AdViewSet
from apps.ads.sp.views.auto_targeting_view import AutoTargetingViewSet
from apps.ads.sp.views.auto_negative_targeting_view import AutoNegativeTargetingViewSet
from apps.ads.sp.views.keyword_view import KeywordViewSet
from apps.ads.sp.views.negative_keyword_view import NegativeKeywordViewSet
from apps.ads.sp.views.time_pricing_strategy_view import TimePricingStrategyViewSet
from apps.ads.sp.views.rule_strategy_view import RuleStrategyViewSet, RuleStrategyGroupViewSet

# v2 Function-Based Views
from apps.ads.sp.views.ad_campaign_submit_view import submit_pending_campaigns
from apps.ads.sp.views.ad_time_pricing_view import trigger_time_pricing
from apps.ads.sp.views.ad_upload_queue_view import bulk_delete_ad_queue, list_ad_queue, retry_ad_queue, upload_ad_xlsx
from apps.ads.sp.views.bid_adjustment_view import trigger_bid_adjustment
from apps.ads.sp.views.campaign_adjustment_view import trigger_campaign_adjustment
from apps.ads.sp.views.optimization_strategy_view import trigger_optimization_strategy
from apps.ads.sp.views.optimization_execution_view import trigger_optimization_execution

__all__ = [
    "AdCampaignViewSet", "AdGroupViewSet", "AdViewSet", "AutoTargetingViewSet",
    "AutoNegativeTargetingViewSet", "KeywordViewSet", "NegativeKeywordViewSet",
    "TimePricingStrategyViewSet", "RuleStrategyViewSet", "RuleStrategyGroupViewSet",
    "submit_pending_campaigns", "trigger_time_pricing",
    "bulk_delete_ad_queue", "list_ad_queue", "retry_ad_queue", "upload_ad_xlsx",
    "trigger_bid_adjustment", "trigger_campaign_adjustment",
    "trigger_optimization_strategy", "trigger_optimization_execution",
]
