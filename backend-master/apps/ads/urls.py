"""广告域 — URL 路由。

所有路径以 ``api/v1/`` 为前缀（由 ``backend_master/urls.py`` 的 include 提供）。
"""
from django.urls import path

from apps.ads.views.profile_options_view import ProfileOptionsViewSet
from apps.ads.views.sku_options_view import SkuOptionsViewSet
from apps.ads.views.enum_labels_view import EnumLabelsViewSet
from apps.ads.views.ad_portfolio_view import AdPortfolioViewSet
from apps.ads.sp.views.campaign_view import AdCampaignViewSet
from apps.ads.sp.views.group_view import AdGroupViewSet
from apps.ads.sp.views.ad_view import AdViewSet
from apps.ads.sp.views.targeting_view import AutoTargetingViewSet
from apps.ads.sp.views.negative_targeting_view import AutoNegativeTargetingViewSet
from apps.ads.sp.views.keyword_view import KeywordViewSet
from apps.ads.sp.views.negative_keyword_view import NegativeKeywordViewSet
from apps.ads.sp.views.adjustment_history_view import get_adjustment_history
from apps.ads.sp.timing.views.time_pricing_strategy_view import TimePricingStrategyViewSet
from apps.ads.sp.rules.views.rule_strategy_view import RuleStrategyViewSet, RuleStrategyGroupViewSet

urlpatterns = [
    # ── 广告活动 ──
    path("ads/campaigns", AdCampaignViewSet.as_view({"post": "list"}), name="ads-campaigns"),
    path("ads/campaigns/detail", AdCampaignViewSet.as_view({"get": "campaign_info"}), name="ads-campaign-detail"),
    path("ads/campaigns/adjust-budget", AdCampaignViewSet.as_view({"post": "adjust_budget"}), name="ads-campaigns-adjust-budget"),
    path("ads/campaigns/adjust-state", AdCampaignViewSet.as_view({"post": "adjust_state"}), name="ads-campaigns-adjust-state"),
    path("ads/campaigns/batch-adjust-state", AdCampaignViewSet.as_view({"post": "batch_adjust_state"}), name="ads-campaigns-batch-adjust-state"),
    path("ads/campaigns/batch-adjust-budget", AdCampaignViewSet.as_view({"post": "batch_adjust_budget"}), name="ads-campaigns-batch-adjust-budget"),

    # ── 选项 ──
    path("ads/options", ProfileOptionsViewSet.as_view({"post": "options"}), name="ads-options"),
    path("ads/sku-options", SkuOptionsViewSet.as_view({"post": "sku_options"}), name="ads-sku-options"),
    path("ads/enum-labels", EnumLabelsViewSet.as_view({"post": "enum_labels"}), name="ads-enum-labels"),
    path("ads/portfolios/options", AdPortfolioViewSet.as_view({"post": "options"}), name="ads-portfolios-options"),

    # ── 广告组 / 广告 ──
    path("ads/ad-groups", AdGroupViewSet.as_view({"post": "list_groups"}), name="ads-adgroups-list"),
    path("ads/ads", AdViewSet.as_view({"post": "list_ads"}), name="ads-ads-list"),

    # ── 自动定位 ──
    path("ads/auto-targeting", AutoTargetingViewSet.as_view({"post": "list_auto_targeting"}), name="ads-auto-targeting-list"),
    path("ads/auto-targeting/adjust-bid", AutoTargetingViewSet.as_view({"post": "adjust_bid"}), name="ads-auto-targeting-adjust-bid"),
    path("ads/auto-targeting/adjust-state", AutoTargetingViewSet.as_view({"post": "adjust_state"}), name="ads-auto-targeting-adjust-state"),
    path("ads/auto-targeting/batch-adjust-state", AutoTargetingViewSet.as_view({"post": "batch_adjust_state"}), name="ads-auto-targeting-batch-adjust-state"),
    path("ads/auto-targeting/batch-adjust-bid", AutoTargetingViewSet.as_view({"post": "batch_adjust_bid"}), name="ads-auto-targeting-batch-adjust-bid"),

    # ── 产品定位 ──
    path("ads/product-targeting", AutoTargetingViewSet.as_view({"post": "list_product_targeting"}), name="ads-product-targeting-list"),
    path("ads/product-targeting/adjust-bid", AutoTargetingViewSet.as_view({"post": "adjust_bid"}), name="ads-product-targeting-adjust-bid"),
    path("ads/product-targeting/adjust-state", AutoTargetingViewSet.as_view({"post": "adjust_state"}), name="ads-product-targeting-adjust-state"),
    path("ads/product-targeting/batch-adjust-state", AutoTargetingViewSet.as_view({"post": "batch_adjust_state"}), name="ads-product-targeting-batch-adjust-state"),
    path("ads/product-targeting/batch-adjust-bid", AutoTargetingViewSet.as_view({"post": "batch_adjust_bid"}), name="ads-product-targeting-batch-adjust-bid"),

    # ── 否定定位 ──
    path("ads/auto-negative-targeting", AutoNegativeTargetingViewSet.as_view({"post": "list_auto_negative_targeting"}), name="ads-auto-negative-targeting-list"),

    # ── 关键词 ──
    path("ads/keywords", KeywordViewSet.as_view({"post": "list_keywords"}), name="ads-keywords-list"),
    path("ads/keywords/adjust-bid", KeywordViewSet.as_view({"post": "adjust_bid"}), name="ads-keywords-adjust-bid"),
    path("ads/keywords/adjust-state", KeywordViewSet.as_view({"post": "adjust_state"}), name="ads-keywords-adjust-state"),
    path("ads/keywords/batch-adjust-state", KeywordViewSet.as_view({"post": "batch_adjust_state"}), name="ads-keywords-batch-adjust-state"),
    path("ads/keywords/batch-adjust-bid", KeywordViewSet.as_view({"post": "batch_adjust_bid"}), name="ads-keywords-batch-adjust-bid"),

    # ── 否定关键词 ──
    path("ads/negative-keywords", NegativeKeywordViewSet.as_view({"post": "list_negative_keywords"}), name="ads-negative-keywords-list"),

    # ── 调整历史 ──
    path("ads/adjustment-history", get_adjustment_history, name="ads-adjustment-history"),

    # ── 分时调价策略 ──
    path("ads/time-pricing-strategy", TimePricingStrategyViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="ads-time-pricing-strategy-list-create"),
    path("ads/time-pricing-strategy/shops", TimePricingStrategyViewSet.as_view({"get": "shops"}), name="ads-time-pricing-strategy-shops"),
    path("ads/time-pricing-strategy/managers", TimePricingStrategyViewSet.as_view({"get": "managers"}), name="ads-time-pricing-strategy-managers"),
    path("ads/time-pricing-strategy/assorts", TimePricingStrategyViewSet.as_view({"get": "assorts"}), name="ads-time-pricing-strategy-assorts"),
    path("ads/time-pricing-strategy/labels", TimePricingStrategyViewSet.as_view({"get": "labels"}), name="ads-time-pricing-strategy-labels"),
    path("ads/time-pricing-strategy/<str:id>/form", TimePricingStrategyViewSet.as_view({"get": "form"}), name="ads-time-pricing-strategy-form"),
    path("ads/time-pricing-strategy/<str:ids>", TimePricingStrategyViewSet.as_view({"put": "update_or_delete", "delete": "update_or_delete"}), name="ads-time-pricing-strategy-update-delete"),

    # ── 广告规则策略 ──
    path("ads/rule-strategy/rules", RuleStrategyViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="ads-rule-strategy-rules-list-create"),
    path("ads/rule-strategy/rules/<str:id>/update", RuleStrategyViewSet.as_view({"put": "update"}), name="ads-rule-strategy-rules-update"),
    path("ads/rule-strategy/rules/<str:id>/delete", RuleStrategyViewSet.as_view({"delete": "destroy"}), name="ads-rule-strategy-rules-delete"),
    path("ads/rule-strategy/rules/<str:id>", RuleStrategyViewSet.as_view({"get": "retrieve"}), name="ads-rule-strategy-rules-detail"),
    path("ads/rule-strategy/groups", RuleStrategyGroupViewSet.as_view({"get": "list_or_create", "post": "list_or_create"}), name="ads-rule-strategy-groups-list-create"),
    path("ads/rule-strategy/groups/<str:id>/update", RuleStrategyGroupViewSet.as_view({"put": "update"}), name="ads-rule-strategy-groups-update"),
    path("ads/rule-strategy/groups/<str:id>/delete", RuleStrategyGroupViewSet.as_view({"delete": "destroy"}), name="ads-rule-strategy-groups-delete"),
    path("ads/rule-strategy/groups/<str:id>/add-rules", RuleStrategyGroupViewSet.as_view({"post": "add_rules"}), name="ads-rule-strategy-groups-add-rules"),
    path("ads/rule-strategy/groups/<str:id>/remove-rule", RuleStrategyGroupViewSet.as_view({"post": "remove_rule"}), name="ads-rule-strategy-groups-remove-rule"),
    path("ads/rule-strategy/groups/<str:id>", RuleStrategyGroupViewSet.as_view({"get": "retrieve"}), name="ads-rule-strategy-groups-detail"),
]
