"""广告创建包（ad_creation）。

包含广告活动和广告组两步提交流程所需的全部服务模块：
  - ad_lx_client              — 底层共享客户端工具
  - ad_campaign_service       — 广告活动创建（Step 1）
  - ad_group_service          — 广告组创建（Step 2）
  - ad_campaign_submit_service — 调度入口
"""

from api_v2.services.ad_creation.ad_campaign_submit_service import process_pending_campaigns

__all__ = ["process_pending_campaigns"]
