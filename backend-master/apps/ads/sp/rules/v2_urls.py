"""广告规则域 — api_v2 路由。"""

from django.urls import path

from apps.ads.sp.rules.views.ad_campaign_submit_view import submit_pending_campaigns
from apps.ads.sp.rules.views.ad_upload_queue_view import bulk_delete_ad_queue, list_ad_queue, retry_ad_queue, upload_ad_xlsx
from apps.ads.sp.rules.views.bid_adjustment_view import trigger_bid_adjustment
from apps.ads.sp.rules.views.campaign_adjustment_view import trigger_campaign_adjustment
from apps.ads.sp.rules.views.optimization_strategy_view import trigger_optimization_strategy
from apps.ads.sp.rules.views.optimization_execution_view import trigger_optimization_execution

urlpatterns = [
    path('ads/upload/', upload_ad_xlsx, name='ads_upload'),
    path('ads/queue/', list_ad_queue, name='ads_queue_list'),
    path('ads/queue/bulk-delete/', bulk_delete_ad_queue, name='ads_queue_bulk_delete'),
    path('ads/queue/retry/', retry_ad_queue, name='ads_queue_retry'),
    path('ads/submit/', submit_pending_campaigns, name='ads_campaign_submit'),
    path('ads/bid-adjustment/run/', trigger_bid_adjustment, name='bid_adjustment_run'),
    path('ads/campaign-adjustment/run/', trigger_campaign_adjustment, name='campaign_adjustment_run'),
    path('ads/optimization-strategy/run/', trigger_optimization_strategy, name='ads_optimization_strategy_run'),
    path('ads/optimization-strategy/execute/', trigger_optimization_execution, name='ads_optimization_strategy_execute'),
]
