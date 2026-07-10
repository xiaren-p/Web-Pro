"""
URL configuration for backend_master project.

All routes registered directly here; the `api_v1/` relay package has been removed.
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from apps.system.views.oidc_login_view import oidc_login_view
from apps.system.views.auth_view import AuthViewSet
from apps.system.views.user_view import UserViewSet
from apps.system.views.profile_view import ProfileViewSet
from apps.system.views.config_view import ConfigViewSet
from apps.system.views.dept_view import DeptViewSet
from apps.system.views.dict_view import DictViewSet
from apps.system.views.log_view import LogViewSet
from apps.system.views.menu_view import MenuViewSet
from apps.system.views.position_view import PositionViewSet
from apps.system.views.codegen_view import CodegenViewSet
from apps.system.views.work_report_view import WorkReportViewSet
from apps.lingxing_basic.views.shop_view import ShopOptionsViewSet
from apps.sales.listing.views.listing_view import SalesProductListingViewSet
from apps.sales.listing.views.listing_tag_view import ListingTagViewSet
from apps.sales.listing.views.image_view import ImageUploadViewSet
from apps.ads.views.shop_profile_view import ShopProfileViewSet
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
from apps.notice.views.notice_view import NoticeViewSet
from apps.nc.views.nc_folder_tree_view import NcFolderTreeViewSet
from apps.common.utils.responses import drf_ok


def api_root(request):
    return drf_ok({"name": "backend_master"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', oidc_login_view, name='login'),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    # ── 认证 ──
    path('api/v1/auth/login', AuthViewSet.as_view({'post': 'login'}), name='auth-login'),
    path('api/v1/auth/refresh-token', csrf_exempt(AuthViewSet.as_view({'post': 'refresh_token'})), name='auth-refresh'),
    path('api/v1/auth/logout', AuthViewSet.as_view({'delete': 'logout', 'get': 'logout', 'post': 'logout'}), name='auth-logout'),
    path('api/v1/auth/captcha', AuthViewSet.as_view({'get': 'captcha'}), name='auth-captcha'),
    path('api/v1/auth/sso-session', AuthViewSet.as_view({'post': 'sso_session'}), name='auth-sso-session'),

    # ── 代码生成 ──
    path('api/v1/codegen/table/page', CodegenViewSet.as_view({'get': 'table_page'}), name='codegen-table-page'),
    path('api/v1/codegen/<str:table_name>/config', CodegenViewSet.as_view({'get': 'config', 'post': 'config', 'delete': 'config'}), name='codegen-config'),
    path('api/v1/codegen/<str:table_name>/preview', CodegenViewSet.as_view({'get': 'preview'}), name='codegen-preview'),
    path('api/v1/codegen/<str:table_name>/download', CodegenViewSet.as_view({'get': 'download'}), name='codegen-download'),

    # ── 用户 ──
    path('api/v1/users/me', UserViewSet.as_view({'get': 'me'}), name='user-me'),
    path('api/v1/users/page', UserViewSet.as_view({'get': 'page'}), name='user-page'),
    path('api/v1/users/<str:user_id>/form', UserViewSet.as_view({'get': 'form'}), name='user-form'),
    path('api/v1/users/profile', UserViewSet.as_view({'get': 'profile_get', 'put': 'profile_put'}), name='user-profile'),
    path('api/v1/users/password', UserViewSet.as_view({'put': 'change_password'}), name='user-change-password'),
    path('api/v1/users/avatar', UserViewSet.as_view({'post': 'upload_avatar'}), name='user-upload-avatar'),
    path('api/v1/users/upload-image', UserViewSet.as_view({'post': 'upload_image'}), name='user-upload-image'),
    path('api/v1/users/options', UserViewSet.as_view({'get': 'options'}), name='user-options'),
    path('api/v1/users', UserViewSet.as_view({'get': 'generic_get', 'post': 'create'}), name='users-create'),
    path('api/v1/users/<str:id>', UserViewSet.as_view({'put': 'update', 'delete': 'delete'}), name='user-update-delete'),
    path('api/v1/users/<str:id>/password/reset', UserViewSet.as_view({'put': 'reset_password'}), name='user-reset-password'),
    path('api/v1/users/mobile/code', ProfileViewSet.as_view({'post': 'send_mobile_code'}), name='user-mobile-code'),
    path('api/v1/users/mobile', ProfileViewSet.as_view({'put': 'bind_mobile'}), name='user-bind-mobile'),
    path('api/v1/users/email/code', ProfileViewSet.as_view({'post': 'send_email_code'}), name='user-email-code'),
    path('api/v1/users/email', ProfileViewSet.as_view({'put': 'bind_email'}), name='user-bind-email'),

    # ── 销售 ──
    path('api/v1/sales/product/listing', SalesProductListingViewSet.as_view({'get': 'page'}), name='sales-product-listing'),
    path('api/v1/sales/product/listing/labels/upsert', SalesProductListingViewSet.as_view({'post': 'upsert_labels'}), name='sales-product-listing-labels-upsert'),
    path('api/v1/sales/product/listing/assort/upsert', SalesProductListingViewSet.as_view({'post': 'upsert_assort'}), name='sales-product-listing-assort-upsert'),
    path('api/v1/sales/product/listing/remark/upsert', SalesProductListingViewSet.as_view({'post': 'upsert_remark'}), name='sales-product-listing-remark-upsert'),
    path('api/v1/sales/listing/tags', ListingTagViewSet.as_view({'get': 'list', 'post': 'create'}), name='sales-listing-tags'),
    path('api/v1/sales/listing/tags/batch-delete', ListingTagViewSet.as_view({'post': 'batch_delete'}), name='sales-listing-tags-batch-delete'),
    path('api/v1/sales/listing/tags/type-options', ListingTagViewSet.as_view({'get': 'type_options'}), name='sales-listing-tags-type-options'),
    path('api/v1/sales/listing/tags/options', ListingTagViewSet.as_view({'get': 'tag_options'}), name='sales-listing-tags-options'),
    path('api/v1/sales/listing/tags/<str:pk>', ListingTagViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='sales-listing-tags-detail'),
    path('api/v1/sales/listing/tags/<str:pk>/status', ListingTagViewSet.as_view({'put': 'update_status'}), name='sales-listing-tags-status'),

    # ── 广告 ──
    path('api/v1/ads/campaigns', AdCampaignViewSet.as_view({'post': 'list'}), name='ads-campaigns'),
    path('api/v1/ads/campaigns/detail', AdCampaignViewSet.as_view({'get': 'campaign_info'}), name='ads-campaign-detail'),
    path('api/v1/ads/campaigns/adjust-budget', AdCampaignViewSet.as_view({'post': 'adjust_budget'}), name='ads-campaigns-adjust-budget'),
    path('api/v1/ads/campaigns/adjust-state', AdCampaignViewSet.as_view({'post': 'adjust_state'}), name='ads-campaigns-adjust-state'),
    path('api/v1/ads/campaigns/batch-adjust-state', AdCampaignViewSet.as_view({'post': 'batch_adjust_state'}), name='ads-campaigns-batch-adjust-state'),
    path('api/v1/ads/campaigns/batch-adjust-budget', AdCampaignViewSet.as_view({'post': 'batch_adjust_budget'}), name='ads-campaigns-batch-adjust-budget'),
    path('api/v1/ads/options', ShopProfileViewSet.as_view({'post': 'options'}), name='ads-options'),
    path('api/v1/ads/sku-options', ShopProfileViewSet.as_view({'post': 'sku_options'}), name='ads-sku-options'),
    path('api/v1/ads/enum-labels', ShopProfileViewSet.as_view({'post': 'enum_labels'}), name='ads-enum-labels'),
    path('api/v1/ads/portfolios/options', AdPortfolioViewSet.as_view({'post': 'options'}), name='ads-portfolios-options'),
    path('api/v1/ads/ad-groups', AdGroupViewSet.as_view({'post': 'list_groups'}), name='ads-adgroups-list'),
    path('api/v1/ads/ads', AdViewSet.as_view({'post': 'list_ads'}), name='ads-ads-list'),
    path('api/v1/ads/auto-targeting', AutoTargetingViewSet.as_view({'post': 'list_auto_targeting'}), name='ads-auto-targeting-list'),
    path('api/v1/ads/auto-targeting/adjust-bid', AutoTargetingViewSet.as_view({'post': 'adjust_bid'}), name='ads-auto-targeting-adjust-bid'),
    path('api/v1/ads/auto-targeting/adjust-state', AutoTargetingViewSet.as_view({'post': 'adjust_state'}), name='ads-auto-targeting-adjust-state'),
    path('api/v1/ads/auto-targeting/batch-adjust-state', AutoTargetingViewSet.as_view({'post': 'batch_adjust_state'}), name='ads-auto-targeting-batch-adjust-state'),
    path('api/v1/ads/auto-targeting/batch-adjust-bid', AutoTargetingViewSet.as_view({'post': 'batch_adjust_bid'}), name='ads-auto-targeting-batch-adjust-bid'),
    path('api/v1/ads/product-targeting', AutoTargetingViewSet.as_view({'post': 'list_product_targeting'}), name='ads-product-targeting-list'),
    path('api/v1/ads/product-targeting/adjust-bid', AutoTargetingViewSet.as_view({'post': 'adjust_bid'}), name='ads-product-targeting-adjust-bid'),
    path('api/v1/ads/product-targeting/adjust-state', AutoTargetingViewSet.as_view({'post': 'adjust_state'}), name='ads-product-targeting-adjust-state'),
    path('api/v1/ads/product-targeting/batch-adjust-state', AutoTargetingViewSet.as_view({'post': 'batch_adjust_state'}), name='ads-product-targeting-batch-adjust-state'),
    path('api/v1/ads/product-targeting/batch-adjust-bid', AutoTargetingViewSet.as_view({'post': 'batch_adjust_bid'}), name='ads-product-targeting-batch-adjust-bid'),
    path('api/v1/ads/auto-negative-targeting', AutoNegativeTargetingViewSet.as_view({'post': 'list_auto_negative_targeting'}), name='ads-auto-negative-targeting-list'),
    path('api/v1/ads/keywords', KeywordViewSet.as_view({'post': 'list_keywords'}), name='ads-keywords-list'),
    path('api/v1/ads/keywords/adjust-bid', KeywordViewSet.as_view({'post': 'adjust_bid'}), name='ads-keywords-adjust-bid'),
    path('api/v1/ads/keywords/adjust-state', KeywordViewSet.as_view({'post': 'adjust_state'}), name='ads-keywords-adjust-state'),
    path('api/v1/ads/keywords/batch-adjust-state', KeywordViewSet.as_view({'post': 'batch_adjust_state'}), name='ads-keywords-batch-adjust-state'),
    path('api/v1/ads/keywords/batch-adjust-bid', KeywordViewSet.as_view({'post': 'batch_adjust_bid'}), name='ads-keywords-batch-adjust-bid'),
    path('api/v1/ads/adjustment-history', get_adjustment_history, name='ads-adjustment-history'),
    path('api/v1/ads/negative-keywords', NegativeKeywordViewSet.as_view({'post': 'list_negative_keywords'}), name='ads-negative-keywords-list'),
    path('api/v1/ads/time-pricing-strategy', TimePricingStrategyViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='ads-time-pricing-strategy-list-create'),
    path('api/v1/ads/time-pricing-strategy/shops', TimePricingStrategyViewSet.as_view({'get': 'shops'}), name='ads-time-pricing-strategy-shops'),
    path('api/v1/ads/time-pricing-strategy/managers', TimePricingStrategyViewSet.as_view({'get': 'managers'}), name='ads-time-pricing-strategy-managers'),
    path('api/v1/ads/time-pricing-strategy/assorts', TimePricingStrategyViewSet.as_view({'get': 'assorts'}), name='ads-time-pricing-strategy-assorts'),
    path('api/v1/ads/time-pricing-strategy/labels', TimePricingStrategyViewSet.as_view({'get': 'labels'}), name='ads-time-pricing-strategy-labels'),
    path('api/v1/ads/time-pricing-strategy/<str:id>/form', TimePricingStrategyViewSet.as_view({'get': 'form'}), name='ads-time-pricing-strategy-form'),
    path('api/v1/ads/time-pricing-strategy/<str:ids>', TimePricingStrategyViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='ads-time-pricing-strategy-update-delete'),
    path('api/v1/ads/rule-strategy/rules', RuleStrategyViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='ads-rule-strategy-rules-list-create'),
    path('api/v1/ads/rule-strategy/rules/<str:id>/update', RuleStrategyViewSet.as_view({'put': 'update'}), name='ads-rule-strategy-rules-update'),
    path('api/v1/ads/rule-strategy/rules/<str:id>/delete', RuleStrategyViewSet.as_view({'delete': 'destroy'}), name='ads-rule-strategy-rules-delete'),
    path('api/v1/ads/rule-strategy/rules/<str:id>', RuleStrategyViewSet.as_view({'get': 'retrieve'}), name='ads-rule-strategy-rules-detail'),
    path('api/v1/ads/rule-strategy/groups', RuleStrategyGroupViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='ads-rule-strategy-groups-list-create'),
    path('api/v1/ads/rule-strategy/groups/<str:id>/update', RuleStrategyGroupViewSet.as_view({'put': 'update'}), name='ads-rule-strategy-groups-update'),
    path('api/v1/ads/rule-strategy/groups/<str:id>/delete', RuleStrategyGroupViewSet.as_view({'delete': 'destroy'}), name='ads-rule-strategy-groups-delete'),
    path('api/v1/ads/rule-strategy/groups/<str:id>/add-rules', RuleStrategyGroupViewSet.as_view({'post': 'add_rules'}), name='ads-rule-strategy-groups-add-rules'),
    path('api/v1/ads/rule-strategy/groups/<str:id>/remove-rule', RuleStrategyGroupViewSet.as_view({'post': 'remove_rule'}), name='ads-rule-strategy-groups-remove-rule'),
    path('api/v1/ads/rule-strategy/groups/<str:id>', RuleStrategyGroupViewSet.as_view({'get': 'retrieve'}), name='ads-rule-strategy-groups-detail'),

    # ── 岗位 ──
    path('api/v1/positions/page', PositionViewSet.as_view({'get': 'page'}), name='positions-page'),
    path('api/v1/positions/options', PositionViewSet.as_view({'get': 'options'}), name='positions-options'),
    path('api/v1/positions', PositionViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='positions-list-create'),
    path('api/v1/positions/<str:position_id>/form', PositionViewSet.as_view({'get': 'form'}), name='position-form'),
    path('api/v1/positions/<str:ids>', PositionViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='position-update-delete'),
    path('api/v1/positions/<str:position_id>/menuIds', PositionViewSet.as_view({'get': 'menu_ids'}), name='position-menu-ids'),
    path('api/v1/positions/<str:position_id>/menus', PositionViewSet.as_view({'put': 'update_menus'}), name='position-update-menus'),

    # ── 通知 ──
    path('api/v1/notices/page', NoticeViewSet.as_view({'get': 'page'}), name='notices-page'),
    path('api/v1/notices/<str:id>/form', NoticeViewSet.as_view({'get': 'form'}), name='notice-form'),
    path('api/v1/notices/<str:id>/publish', NoticeViewSet.as_view({'post': 'publish'}), name='notice-publish'),
    path('api/v1/notices/<str:id>/revoke', NoticeViewSet.as_view({'post': 'revoke'}), name='notice-revoke'),
    path('api/v1/notices/<str:id>/read', NoticeViewSet.as_view({'post': 'read'}), name='notice-read'),
    path('api/v1/notices/<str:id>/detail', NoticeViewSet.as_view({'get': 'detail_plain'}), name='notice-detail'),
    path('api/v1/notices/read-all', NoticeViewSet.as_view({'post': 'read_all'}), name='notice-read-all'),
    path('api/v1/notices/my-page', NoticeViewSet.as_view({'get': 'my_page'}), name='notices-my-page'),
    path('api/v1/notices/export', NoticeViewSet.as_view({'get': 'export_data'}), name='notices-export'),
    path('api/v1/notices', NoticeViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='notices-list-create'),
    path('api/v1/notices/<str:ids>', NoticeViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='notice-update-delete'),

    # ── NC ──
    path('api/v1/nc/folder-tree/groups', NcFolderTreeViewSet.as_view({'get': 'group_list'}), name='nc-folder-tree-groups'),
    path('api/v1/nc/folder-tree/list', NcFolderTreeViewSet.as_view({'get': 'list_folder'}), name='nc-folder-tree-list'),
    path('api/v1/nc/folder-tree/mkdir', NcFolderTreeViewSet.as_view({'post': 'mkdir'}), name='nc-folder-tree-mkdir'),
    path('api/v1/nc/folder-tree/folder-delete-preview', NcFolderTreeViewSet.as_view({'get': 'folder_delete_preview'}), name='nc-folder-tree-folder-delete-preview'),
    path('api/v1/nc/folder-tree/folder', NcFolderTreeViewSet.as_view({'delete': 'delete_folder'}), name='nc-folder-tree-delete-folder'),
    path('api/v1/nc/folder-tree/set-rule', NcFolderTreeViewSet.as_view({'post': 'set_rule'}), name='nc-folder-tree-set-rule'),
    path('api/v1/nc/folder-tree/set-rules-batch', NcFolderTreeViewSet.as_view({'post': 'set_rules_batch'}), name='nc-folder-tree-set-rules-batch'),
    re_path(r'^api/v1/nc/folder-tree/rule/(?P<pk>\d+)$', NcFolderTreeViewSet.as_view({'delete': 'delete_rule'}), name='nc-folder-tree-delete-rule'),
    path('api/v1/nc/folder-tree/path-rules', NcFolderTreeViewSet.as_view({'get': 'path_rules'}), name='nc-folder-tree-path-rules'),
    path('api/v1/nc/folder-tree/user-tree', NcFolderTreeViewSet.as_view({'get': 'user_tree'}), name='nc-folder-tree-user-tree'),

    # ── 菜单 ──
    path('api/v1/menus/routes', MenuViewSet.as_view({'get': 'routes'}), name='menus-routes'),
    path('api/v1/menus/tree', MenuViewSet.as_view({'get': 'tree'}), name='menus-tree'),
    path('api/v1/menus', MenuViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='menus-list-create'),
    path('api/v1/menus/options', MenuViewSet.as_view({'get': 'options'}), name='menus-options'),
    path('api/v1/menus/<str:id>/form', MenuViewSet.as_view({'get': 'form'}), name='menu-form'),
    path('api/v1/menus/<str:id>', MenuViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='menu-update-delete'),

    # ── 店铺 ──
    path('api/v1/shops/options', ShopOptionsViewSet.as_view({'get': 'shops'}), name='shops-options'),
    path('api/v1/shops/owners', ShopOptionsViewSet.as_view({'get': 'owners'}), name='shops-owners'),

    # ── 爬虫 ──
    path('api/v1/crawler/', include('apps.crawler.urls')),

    # ── 日志 ──
    path('api/v1/logs/page', LogViewSet.as_view({'get': 'page'}), name='logs-page'),
    path('api/v1/logs/visit-trend', LogViewSet.as_view({'get': 'visit_trend'}), name='logs-visit-trend'),
    path('api/v1/logs/visit-stats', LogViewSet.as_view({'get': 'visit_stats'}), name='logs-visit-stats'),

    # ── 字典 ──
    path('api/v1/dicts/page', DictViewSet.as_view({'get': 'page'}), name='dicts-page'),
    path('api/v1/dicts', DictViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='dicts-list-create'),
    path('api/v1/dicts/<str:id>/form', DictViewSet.as_view({'get': 'form'}), name='dict-form'),
    path('api/v1/dicts/<str:ids>', DictViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='dict-update-delete'),
    path('api/v1/dicts/<str:dict_code>/items', DictViewSet.as_view({'get': 'items_list_or_create', 'post': 'items_list_or_create'}), name='dict-items-list-create'),
    path('api/v1/dicts/<str:dict_code>/items/page', DictViewSet.as_view({'get': 'items_page'}), name='dict-items-page'),
    path('api/v1/dicts/<str:dict_code>/items/<str:item_id>/form', DictViewSet.as_view({'get': 'item_form'}), name='dict-item-form'),
    path('api/v1/dicts/<str:dict_code>/items/options', DictViewSet.as_view({'get': 'item_options'}), name='dict-item-options'),
    path('api/v1/dicts/<str:dict_code>/items/<str:item_id>', DictViewSet.as_view({'put': 'item_update_or_delete', 'delete': 'item_update_or_delete'}), name='dict-item-update-delete'),

    # ── 部门 ──
    path('api/v1/depts', DeptViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='depts-list-create'),
    path('api/v1/depts/tree', DeptViewSet.as_view({'get': 'tree'}), name='depts-tree'),
    path('api/v1/depts/options', DeptViewSet.as_view({'get': 'options'}), name='depts-options'),
    path('api/v1/depts/<str:id>/form', DeptViewSet.as_view({'get': 'form'}), name='dept-form'),
    path('api/v1/depts/<str:ids>', DeptViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='dept-update-delete'),

    # ── 配置 ──
    path('api/v1/configs/page', ConfigViewSet.as_view({'get': 'page'}), name='configs-page'),
    path('api/v1/configs', ConfigViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='configs-list-create'),
    path('api/v1/configs/<str:id>/form', ConfigViewSet.as_view({'get': 'form'}), name='config-form'),
    path('api/v1/configs/refresh-cache', ConfigViewSet.as_view({'post': 'refresh_cache'}), name='configs-refresh-cache'),
    path('api/v1/configs/<str:ids>', ConfigViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='config-update-delete'),

    # ── 图片上传 ──
    path('api/v1/image-uploads/upload_image', ImageUploadViewSet.as_view({'post': 'upload_image'}), name='image-upload-upload-image'),
    path('api/v1/image-uploads/page', ImageUploadViewSet.as_view({'get': 'page'}), name='image-upload-page'),
    path('api/v1/image-uploads/queue', ImageUploadViewSet.as_view({'get': 'queue'}), name='image-upload-queue'),
    path('api/v1/image-uploads/import_csv', ImageUploadViewSet.as_view({'post': 'import_csv'}), name='image-upload-import-csv'),
    path('api/v1/image-uploads/batch_sync', ImageUploadViewSet.as_view({'post': 'batch_sync'}), name='image-upload-batch-sync'),
    path('api/v1/image-uploads/<str:pk>/form', ImageUploadViewSet.as_view({'get': 'form'}), name='image-upload-form'),
    path('api/v1/image-uploads/<str:pk>/sync', ImageUploadViewSet.as_view({'post': 'sync'}), name='image-upload-sync'),
    path('api/v1/image-uploads', ImageUploadViewSet.as_view({'post': 'create'}), name='image-upload-create'),
    path('api/v1/image-uploads/<str:pk>', ImageUploadViewSet.as_view({'put': 'update', 'delete': 'delete_ids'}), name='image-upload-update-delete'),

    # ── 工作汇报 ──
    path('api/v1/work-report/team/stats/details', WorkReportViewSet.as_view({'get': 'team_stats_details'}), name='work-report-team-stats-details'),
    path('api/v1/work-report/team/stats', WorkReportViewSet.as_view({'get': 'team_stats'}), name='work-report-team-stats'),
    path('api/v1/work-report', WorkReportViewSet.as_view({'get': 'list'}), name='work-report-list'),
    path('api/v1/work-report/<str:pk>', WorkReportViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='work-report-detail'),

    # ── 独立路由模块 ──
    path('api/v1/', include('apps.ads.sp.timing.urls')),
    path('api/v1/', include('apps.ads.sp.rules.urls')),
    path('api/v1/', include('apps.system.urls')),
    path('api/v1/common/', include('apps.common.urls')),
    path('api/v1/ai/', include('apps.ai.urls')),

    # ── 旧路径重定向 ──
    path('crawler/logs', RedirectView.as_view(url='/api/v1/crawler/logs', permanent=False)),

    # ── API 根 ──
    path('api/v1/', api_root, name='api-root'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    if getattr(settings, "DJANGO_SERVE_MEDIA", True):
        urlpatterns += [
            re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        ]
