"""广告域 — api_v2 路由（Function-Based View 模式）。"""

from django.urls import path

from apps.ads.views.ad_campaign_submit_view import submit_pending_campaigns
from apps.ads.views.ad_time_pricing_view import trigger_time_pricing
from apps.ads.views.ad_upload_queue_view import bulk_delete_ad_queue, list_ad_queue, retry_ad_queue, upload_ad_xlsx
from apps.ads.views.bid_adjustment_view import trigger_bid_adjustment
from apps.ads.views.campaign_adjustment_view import trigger_campaign_adjustment
from apps.ads.views.optimization_strategy_view import trigger_optimization_strategy
from apps.ads.views.optimization_execution_view import trigger_optimization_execution

urlpatterns = [
    # 广告上传队列
    path('ads/upload/', upload_ad_xlsx, name='ads_upload'),
    path('ads/queue/', list_ad_queue, name='ads_queue_list'),
    path('ads/queue/bulk-delete/', bulk_delete_ad_queue, name='ads_queue_bulk_delete'),
    path('ads/queue/retry/', retry_ad_queue, name='ads_queue_retry'),
    path('ads/submit/', submit_pending_campaigns, name='ads_campaign_submit'),
    # 分时策略执行
    path('ads/time-pricing/execute/', trigger_time_pricing, name='ads_time_pricing_execute'),
    # 竞价调整执行
    path('ads/bid-adjustment/run/', trigger_bid_adjustment, name='bid_adjustment_run'),
    # 广告活动调整执行
    path('ads/campaign-adjustment/run/', trigger_campaign_adjustment, name='campaign_adjustment_run'),
    # SP广告优化策略匹配
    path('ads/optimization-strategy/run/', trigger_optimization_strategy, name='ads_optimization_strategy_run'),
    # SP广告优化策略执行
    path('ads/optimization-strategy/execute/', trigger_optimization_execution, name='ads_optimization_strategy_execute'),
]
