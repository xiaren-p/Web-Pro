"""广告域 — SP 服务层。"""
from apps.ads.sp.rules.services.ad_creation.ad_campaign_submit_service import process_pending_campaigns

__all__ = ["process_pending_campaigns"]
