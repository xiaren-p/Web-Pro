"""广告域 — SP 模型层（基础 SP 模型 + v2 执行模型 + 规则/策略）。"""
# ——— v2 执行模型 ———
from apps.ads.sp.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus, ManualRulesStatus
from apps.ads.sp.models.ad_upload_queue import AdUploadQueue, AdParseStatus
from apps.ads.sp.models.sp_ad_optimization_strategy import SpAdOptimizationStrategy
from apps.ads.sp.models.sp_bid_adjustment import SpBidAdjustment, ExecutionTypeChoices, AdjustmentStatusChoices, ExecutionStatusChoices, PauseEntityTypeChoices
from apps.ads.sp.models.sp_campaign_adjustment import SpCampaignAdjustment, CampaignExecutionTypeChoices
from apps.ads.sp.models.lx_api_err import LxApiErr

# ——— v1 规则/策略 ———
from apps.ads.sp.models.lx_ad_rule import LxAdRule, AdRuleStatus, EffectiveType, ComparisonTarget, AddKeywordMatchType, AddKeywordBidType
from apps.ads.sp.models.lx_ad_rule_group import LxAdRuleGroup
from apps.ads.sp.models.lx_time_pricing_strategy import LxTimePricingStrategy, StrategyStatus, StrategyType, BaseValueType, ExecutionResultType

# ——— v1 SP 基础数据 ———
from apps.ads.sp.models.lx_ads_portfolio import LxAdsPortfolio, PortfolioInBudgetStatus
from apps.ads.sp.models.lx_ads_profile import LxAdsProfile, AdsProfileStatus, AdsProfileType
from apps.ads.sp.models.lx_sp_campaign import LxSpCampaign, SpCampaignTargetingType
from apps.ads.sp.models.lx_sp_ad_group import LxSpAdGroup
from apps.ads.sp.models.lx_sp_ad import LxSpAd
from apps.ads.sp.models.lx_sp_keyword import LxSpKeyword, SpKeywordMatchType
from apps.ads.sp.models.lx_sp_target import LxSpTarget, SpTargetExpressionType
from apps.ads.sp.models.lx_sp_negative_target import LxSpNegativeTarget, NegativeTargetType

# ——— v1 报表 ———
from apps.ads.sp.models.lx_sp_campaign_report import LxSpCampaignReport
from apps.ads.sp.models.lx_sp_ad_group_report import LxSpAdGroupReport
from apps.ads.sp.models.lx_sp_ad_report import LxSpAdReport
from apps.ads.sp.models.lx_sp_keyword_report import LxSpKeywordReport
from apps.ads.sp.models.lx_sp_target_report import LxSpTargetReport
from apps.ads.sp.models.lx_sp_search_term_report import LxSpSearchTermReport

__all__ = [
    'AdTimePricingHit', 'TimePricingHitStatus', 'ManualRulesStatus',
    'AdUploadQueue', 'AdParseStatus',
    'SpAdOptimizationStrategy',
    'SpBidAdjustment', 'ExecutionTypeChoices', 'AdjustmentStatusChoices', 'ExecutionStatusChoices', 'PauseEntityTypeChoices',
    'SpCampaignAdjustment', 'CampaignExecutionTypeChoices',
    'LxApiErr',
    'LxAdRule', 'AdRuleStatus', 'EffectiveType', 'ComparisonTarget', 'AddKeywordMatchType', 'AddKeywordBidType',
    'LxAdRuleGroup',
    'LxTimePricingStrategy', 'StrategyStatus', 'StrategyType', 'BaseValueType', 'ExecutionResultType',
    'LxAdsPortfolio', 'PortfolioInBudgetStatus',
    'LxAdsProfile', 'AdsProfileStatus', 'AdsProfileType',
    'LxSpCampaign', 'SpCampaignTargetingType',
    'LxSpAdGroup', 'LxSpAd',
    'LxSpKeyword', 'SpKeywordMatchType',
    'LxSpTarget', 'SpTargetExpressionType',
    'LxSpNegativeTarget', 'NegativeTargetType',
    'LxSpCampaignReport', 'LxSpAdGroupReport', 'LxSpAdReport',
    'LxSpKeywordReport', 'LxSpTargetReport', 'LxSpSearchTermReport',
]
