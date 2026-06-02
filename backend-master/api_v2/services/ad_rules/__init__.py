"""广告规则服务包——可复用的广告数据查询、产品画像提取与分时策略匹配。"""

from api_v2.services.ad_rules.campaign_product_service import (
    get_asins_by_campaign,
    get_campaign_product_profile,
    get_product_fields_by_asins,
)
from api_v2.services.ad_rules.strategy_matcher import (
    check_field_match,
    check_time_match,
    match_strategy_against_product,
)
from api_v2.services.ad_rules.ad_time_pricing_service import (
    match_strategy,
    process_new_ads,
)

__all__ = [
    # 产品查询
    "get_asins_by_campaign",
    "get_product_fields_by_asins",
    "get_campaign_product_profile",
    # 策略匹配
    "check_time_match",
    "check_field_match",
    "match_strategy_against_product",
    "match_strategy",
    "process_new_ads",
]
