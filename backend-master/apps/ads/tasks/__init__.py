"""广告 app 任务注册入口。autodiscover_tasks 只扫描 apps.ads.tasks，此处从子模块重导出。"""
from apps.ads.sp.tasks import refresh_listing_caches
from apps.ads.sp.rules.tasks import (
    submit_pending_campaigns_task,
    run_bid_adjustment_task,
    run_campaign_adjustment_task,
    run_optimization_strategy_task,
    run_optimization_execution_task,
)
from apps.ads.sp.timing.tasks import (
    run_ad_time_pricing_task,
    run_time_pricing_task,
)

__all__ = [
    "refresh_listing_caches",
    "submit_pending_campaigns_task",
    "run_bid_adjustment_task",
    "run_campaign_adjustment_task",
    "run_optimization_strategy_task",
    "run_optimization_execution_task",
    "run_ad_time_pricing_task",
    "run_time_pricing_task",
]
