"""
api_v1 路由表

为了方便维护，所有路由均分段标注模块名，并映射到 `views.py` 中对应的 ViewSet 方法。
保持路径、方法与前端完全一致。
"""

from django.urls import path, re_path
from django.views.decorators.csrf import csrf_exempt
from api_v1 import views

urlpatterns = [
    # 认证模块
    path('auth/login', views.AuthViewSet.as_view({'post': 'login'}), name='auth-login'),
    path('auth/refresh-token', csrf_exempt(views.AuthViewSet.as_view({'post': 'refresh_token'})), name='auth-refresh'),
    path('auth/logout', views.AuthViewSet.as_view({'delete': 'logout', 'get': 'logout', 'post': 'logout'}), name='auth-logout'),
    path('auth/captcha', views.AuthViewSet.as_view({'get': 'captcha'}), name='auth-captcha'),

    # 文件管理模块已移除（文件上传/目录/分享/去重/哈希任务）。如需恢复请参考历史版本。

    # 代码生成
    path('codegen/table/page', views.CodegenViewSet.as_view({'get': 'table_page'}), name='codegen-table-page'),
    path('codegen/<str:table_name>/config', views.CodegenViewSet.as_view({'get': 'config', 'post': 'config', 'delete': 'config'}), name='codegen-config'),
    path('codegen/<str:table_name>/preview', views.CodegenViewSet.as_view({'get': 'preview'}), name='codegen-preview'),
    path('codegen/<str:table_name>/download', views.CodegenViewSet.as_view({'get': 'download'}), name='codegen-download'),

    # 用户模块（含手机号/邮箱绑定由 ProfileViewSet 提供）
    path('users/me', views.UserViewSet.as_view({'get': 'me'}), name='user-me'),
    path('users/page', views.UserViewSet.as_view({'get': 'page'}), name='user-page'),
    path('users/<str:user_id>/form', views.UserViewSet.as_view({'get': 'form'}), name='user-form'),
    # 将所有静态子路径放在 catch-all 之前，避免被 users/<str:id> 抢占
    path('users/template', views.UserViewSet.as_view({'get': 'template'}), name='user-template'),
    path('users/export', views.UserViewSet.as_view({'get': 'export'}), name='user-export'),
    path('users/import', views.UserViewSet.as_view({'post': 'import_users'}), name='user-import'),
    path('users/profile', views.UserViewSet.as_view({'get': 'profile_get', 'put': 'profile_put'}), name='user-profile'),
    path('users/password', views.UserViewSet.as_view({'put': 'change_password'}), name='user-change-password'),
    path('users/avatar', views.UserViewSet.as_view({'post': 'upload_avatar'}), name='user-upload-avatar'),
    path('users/upload-image', views.UserViewSet.as_view({'post': 'upload_image'}), name='user-upload-image'),
    # 静态子路径需置于 catch-all 之前
    path('users/options', views.UserViewSet.as_view({'get': 'options'}), name='user-options'),
    path('users/cloud-create', views.UserViewSet.as_view({'post': 'cloud_create'}), name='user-cloud-create'),
    # 列表/创建
    path('users', views.UserViewSet.as_view({'get': 'generic_get'}), name='users-create-or-template'),
    # 最后放置 catch-all 的单资源路径
    path('users/<str:id>', views.UserViewSet.as_view({'put': 'update', 'delete': 'delete'}), name='user-update-delete'),
    path('users/<str:id>/password/reset', views.UserViewSet.as_view({'put': 'reset_password'}), name='user-reset-password'),
    # DRF ViewSet for mobile/email code and binding with serializer validation
    path('users/mobile/code', views.ProfileViewSet.as_view({'post': 'send_mobile_code'}), name='user-mobile-code'),
    path('users/mobile', views.ProfileViewSet.as_view({'put': 'bind_mobile'}), name='user-bind-mobile'),
    path('users/email/code', views.ProfileViewSet.as_view({'post': 'send_email_code'}), name='user-email-code'),

    # 销售相关
    path('sales/product/listing', views.SalesProductListingViewSet.as_view({'get': 'page', }), name='sales-product-listing'),
    path('sales/product/listing/labels/upsert', views.SalesProductListingViewSet.as_view({'post': 'upsert_labels'}), name='sales-product-listing-labels-upsert'),
    path('sales/product/listing/assort/upsert', views.SalesProductListingViewSet.as_view({'post': 'upsert_assort'}), name='sales-product-listing-assort-upsert'),

    # 广告模块
    path('ads/campaigns', views.AdCampaignViewSet.as_view({'post': 'list', }), name='ads-campaigns'),
    path('ads/campaigns/detail', views.AdCampaignViewSet.as_view({'get': 'campaign_info', }), name='ads-campaign-detail'),
    path('ads/options', views.ShopProfileViewSet.as_view({'post': 'options', }), name='ads-options'),
    path('ads/portfolios/options', views.AdPortfolioViewSet.as_view({'post': 'options', }), name='ads-portfolios-options'),
    path('ads/ad-groups', views.AdGroupViewSet.as_view({'post': 'list_groups', }), name='ads-adgroups-list'),

    path('users/email', views.ProfileViewSet.as_view({'put': 'bind_email'}), name='user-bind-email'),
    # moved above

    # 角色模块（已接入 ORM）
    path('roles/page', views.RoleViewSet.as_view({'get': 'page'}), name='roles-page'),
    path('roles/options', views.RoleViewSet.as_view({'get': 'options'}), name='roles-options'),
    path('roles', views.RoleViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='roles-list-create'),
    path('roles/<str:role_id>/form', views.RoleViewSet.as_view({'get': 'form'}), name='role-form'),
    path('roles/<str:ids>', views.RoleViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='role-update-delete'),
    path('roles/<str:role_id>/menuIds', views.RoleViewSet.as_view({'get': 'menu_ids'}), name='role-menu-ids'),
    path('roles/<str:role_id>/menus', views.RoleViewSet.as_view({'put': 'update_menus'}), name='role-update-menus'),

    # 通知公告
    path('notices/page', views.NoticeViewSet.as_view({'get': 'page'}), name='notices-page'),
    path('notices/<str:id>/form', views.NoticeViewSet.as_view({'get': 'form'}), name='notice-form'),
    path('notices/<str:id>/publish', views.NoticeViewSet.as_view({'post': 'publish'}), name='notice-publish'),
    path('notices/<str:id>/revoke', views.NoticeViewSet.as_view({'post': 'revoke'}), name='notice-revoke'),
    path('notices/<str:id>/read', views.NoticeViewSet.as_view({'post': 'read'}), name='notice-read'),
    path('notices/<str:id>/detail', views.NoticeViewSet.as_view({'get': 'detail_plain'}), name='notice-detail'),
    path('notices/read-all', views.NoticeViewSet.as_view({'post': 'read_all'}), name='notice-read-all'),
    path('notices/my-page', views.NoticeViewSet.as_view({'get': 'my_page'}), name='notices-my-page'),
    path('notices/export', views.NoticeViewSet.as_view({'get': 'export_data'}), name='notices-export'),
    path('notices', views.NoticeViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='notices-list-create'),
    path('notices/<str:ids>', views.NoticeViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='notice-update-delete'),

    # 菜单与动态路由
    path('menus/routes', views.MenuViewSet.as_view({'get': 'routes'}), name='menus-routes'),
    path('menus/tree', views.MenuViewSet.as_view({'get': 'tree'}), name='menus-tree'),
    path('menus', views.MenuViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='menus-list-create'),
    path('menus/options', views.MenuViewSet.as_view({'get': 'options'}), name='menus-options'),
    # 店铺下拉（通过 LingXing OpenAPI 获取）
    path('shops/options', views.SellerViewSet.as_view({'get': 'options'}), name='shops-options'),
    # Listing 负责人下拉（通过 LingXing OpenAPI 获取账号列表）
    path('shops/owners', views.SellerViewSet.as_view({'get': 'owners'}), name='shops-owners'),
    # 亏损报表（使用 LingXing OpenAPI 获取并筛选毛利润为负的数据）
    # 迁移为两步缓存模型：先同步/触发刷新 -> 再按 cache key 读取数据
    path('statistics/lossmakingorders_sync', views.StatisticsViewSet.as_view({'post': 'lossmaking_orders_sync'}), name='statistics-lossmaking-orders-sync'),
    path('statistics/lossmakingorders_data', views.StatisticsViewSet.as_view({'post': 'lossmaking_orders_data'}), name='statistics-lossmaking-orders-data'),
    # 月度亏损订单统计（全部中文字段） - CRUD & 查询，查询参数：月份（月份）与负责人（负责人）
    path('statistics/monthly-loss', views.MonthlyLossViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='statistics-monthly-loss-list-create'),
    path('statistics/monthly-loss/download', views.MonthlyLossViewSet.as_view({'get': 'download', 'post': 'download'}), name='statistics-monthly-loss-download'),
    path('statistics/monthly-loss/<str:id>/form', views.MonthlyLossViewSet.as_view({'get': 'form'}), name='statistics-monthly-loss-form'),
    path('statistics/monthly-loss/<str:ids>', views.MonthlyLossViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='statistics-monthly-loss-update-delete'),
    # 月度前20天亏损（全部中文字段） - CRUD & 查询
    path('statistics/monthly-loss-first20', views.MonthlyLossFirst20ViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='statistics-monthly-loss-first20-list-create'),
    path('statistics/monthly-loss-first20/download', views.MonthlyLossFirst20ViewSet.as_view({'get': 'download', 'post': 'download'}), name='statistics-monthly-loss-first20-download'),
    path('statistics/monthly-loss-first20/<str:id>/form', views.MonthlyLossFirst20ViewSet.as_view({'get': 'form'}), name='statistics-monthly-loss-first20-form'),
    path('statistics/monthly-loss-first20/<str:ids>', views.MonthlyLossFirst20ViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='statistics-monthly-loss-first20-update-delete'),
    path('menus/<str:id>/form', views.MenuViewSet.as_view({'get': 'form'}), name='menu-form'),
    path('menus/<str:id>', views.MenuViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='menu-update-delete'),

    # 数据采集节点（开放接口，无需认证）
    path('crawler/conf', views.CrawlerConfViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='crawler-conf-list'),
    path('crawler/conf/<str:id>/form', views.CrawlerConfViewSet.as_view({'get': 'form'}), name='crawler-conf-form'),
    path('crawler/conf/<str:ids>', views.CrawlerConfViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='crawler-conf-update-delete'),
    # 卖家精灵账号配置（开放接口，无需认证）
    path('crawler/seller', views.CrawlerSellerViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='crawler-seller-list'),
    path('crawler/seller/<str:id>/form', views.CrawlerSellerViewSet.as_view({'get': 'form'}), name='crawler-seller-form'),
    path('crawler/seller/<str:ids>', views.CrawlerSellerViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='crawler-seller-update-delete'),
    # 爬虫日志（开放接口）：分页查询与写入
    path('crawler/logs/page', views.CrawlerLogViewSet.as_view({'get': 'page'}), name='crawler-logs-page'),
    path('crawler/logs', views.CrawlerLogViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='crawler-logs-list-create'),

    # 爬取类目（分页公开，写入需认证）
    path('crawler/category/page', views.CrawlerCategoryViewSet.as_view({'get': 'page'}), name='crawler-category-page'),
    path('crawler/category/sites', views.CrawlerCategoryViewSet.as_view({'get': 'sites'}), name='crawler-category-sites'),
    path('crawler/category', views.CrawlerCategoryViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='crawler-category-list'),
    path('crawler/category/<str:id>/form', views.CrawlerCategoryViewSet.as_view({'get': 'form'}), name='crawler-category-form'),
    path('crawler/category/<str:id>/times', views.CrawlerCategoryViewSet.as_view({'get': 'times'}), name='crawler-category-times'),
    path('crawler/category/<str:id>/file/check', views.CrawlerCategoryViewSet.as_view({'get': 'file_check'}), name='crawler-category-file-check'),
    path('crawler/category/<str:id>/file', views.CrawlerCategoryViewSet.as_view({'get': 'file'}), name='crawler-category-file'),
    path('crawler/category/<str:ids>', views.CrawlerCategoryViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='crawler-category-update-delete'),


    # 日志
    path('logs/page', views.LogViewSet.as_view({'get': 'page'}), name='logs-page'),
    path('logs/visit-trend', views.LogViewSet.as_view({'get': 'visit_trend'}), name='logs-visit-trend'),
    path('logs/visit-stats', views.LogViewSet.as_view({'get': 'visit_stats'}), name='logs-visit-stats'),

    # 字典与字典项
    path('dicts/page', views.DictViewSet.as_view({'get': 'page'}), name='dicts-page'),
    path('dicts', views.DictViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='dicts-list-create'),
    path('dicts/<str:id>/form', views.DictViewSet.as_view({'get': 'form'}), name='dict-form'),
    path('dicts/<str:ids>', views.DictViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='dict-update-delete'),
    path('dicts/<str:dict_code>/items', views.DictViewSet.as_view({'get': 'items_list_or_create', 'post': 'items_list_or_create'}), name='dict-items-list-create'),
    path('dicts/<str:dict_code>/items/page', views.DictViewSet.as_view({'get': 'items_page'}), name='dict-items-page'),
    path('dicts/<str:dict_code>/items/<str:item_id>/form', views.DictViewSet.as_view({'get': 'item_form'}), name='dict-item-form'),

    # additional dict item routes for compatibility
    path('dicts/<str:dict_code>/items/options', views.DictViewSet.as_view({'get': 'item_options'}), name='dict-item-options'),
    path('dicts/<str:dict_code>/items/<str:item_id>', views.DictViewSet.as_view({'put': 'item_update_or_delete', 'delete': 'item_update_or_delete'}), name='dict-item-update-delete'),

    # 部门
    path('depts', views.DeptViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='depts-list-create'),
    path('depts/tree', views.DeptViewSet.as_view({'get': 'tree'}), name='depts-tree'),
    path('depts/options', views.DeptViewSet.as_view({'get': 'options'}), name='depts-options'),
    path('depts/<str:id>/form', views.DeptViewSet.as_view({'get': 'form'}), name='dept-form'),
    path('depts/<str:ids>', views.DeptViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='dept-update-delete'),

    # 参数配置
    path('configs/page', views.ConfigViewSet.as_view({'get': 'page'}), name='configs-page'),
    path('configs', views.ConfigViewSet.as_view({'get': 'list_or_create', 'post': 'list_or_create'}), name='configs-list-create'),
    path('configs/<str:id>/form', views.ConfigViewSet.as_view({'get': 'form'}), name='config-form'),
    # 注意：将 refresh-cache 放在 catch-all 之前，避免被 <ids> 匹配导致 405
    path('configs/refresh-cache', views.ConfigViewSet.as_view({'post': 'refresh_cache'}), name='configs-refresh-cache'),
    path('configs/<str:ids>', views.ConfigViewSet.as_view({'put': 'update_or_delete', 'delete': 'update_or_delete'}), name='config-update-delete'),

    # 文件管理模块已彻底移除（相关路由和实现已删除）。

    # Image Upload
    path('image-uploads/upload_image', views.ImageUploadViewSet.as_view({'post': 'upload_image'}), name='image-upload-upload-image'),
    path('image-uploads/page', views.ImageUploadViewSet.as_view({'get': 'page'}), name='image-upload-page'),
    path('image-uploads/queue', views.ImageUploadViewSet.as_view({'get': 'queue'}), name='image-upload-queue'),
    path('image-uploads/import_csv', views.ImageUploadViewSet.as_view({'post': 'import_csv'}), name='image-upload-import-csv'),
    path('image-uploads/batch_sync', views.ImageUploadViewSet.as_view({'post': 'batch_sync'}), name='image-upload-batch-sync'),
    path('image-uploads/<str:pk>/form', views.ImageUploadViewSet.as_view({'get': 'form'}), name='image-upload-form'),
    path('image-uploads/<str:pk>/sync', views.ImageUploadViewSet.as_view({'post': 'sync'}), name='image-upload-sync'),
    path('image-uploads', views.ImageUploadViewSet.as_view({'post': 'create'}), name='image-upload-create'),
    path('image-uploads/<str:pk>', views.ImageUploadViewSet.as_view({'put': 'update', 'delete': 'delete_ids'}), name='image-upload-update-delete'),

    # 根
    # 天气
    # 工作汇报
    path('work-report/team/stats/details', views.WorkReportViewSet.as_view({'get': 'team_stats_details'}), name='work-report-team-stats-details'),
    path('work-report/team/stats', views.WorkReportViewSet.as_view({'get': 'team_stats'}), name='work-report-team-stats'),
    path('work-report', views.WorkReportViewSet.as_view({'get': 'list', }), name='work-report-list'),
    path('work-report/<str:pk>', views.WorkReportViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='work-report-detail'),

    path('weather/live', views.WeatherViewSet.as_view({'get': 'live'}), name='weather-live'),
    path('', views.root_index, name='api-root'),
]



