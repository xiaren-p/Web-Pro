"""api_v2 路由分发。"""

from django.urls import path

from api_v2.views.ad_campaign_submit_view import submit_pending_campaigns
from api_v2.views.ad_upload_queue_view import (
    bulk_delete_ad_queue,
    list_ad_queue,
    upload_ad_xlsx,
)
from api_v2.views.app_view import (
    create_app,
    delete_app,
    list_apps,
    rotate_secret,
)
from api_v2.views.task_view import cancel_workflow, get_workflow_status, start_workflow

app_name = 'api_v2'

urlpatterns = [
    # 工作流任务接口
    path('workflow/', start_workflow, name='workflow_start'),
    path('workflow/<int:execution_id>/', get_workflow_status, name='workflow_status'),
    path('workflow/<int:execution_id>/cancel/', cancel_workflow, name='workflow_cancel'),

    # 开发者应用管理接口（仅对登录用户开放）
    path('developer/apps/', list_apps, name='developer_apps_list'),
    path('developer/apps/create/', create_app, name='developer_apps_create'),
    path('developer/apps/<int:app_id>/', delete_app, name='developer_apps_delete'),
    path('developer/apps/<int:app_id>/rotate-secret/', rotate_secret, name='developer_apps_rotate'),

    # 广告上传队列接口
    path('ads/upload/', upload_ad_xlsx, name='ads_upload'),
    path('ads/queue/', list_ad_queue, name='ads_queue_list'),
    path('ads/queue/bulk-delete/', bulk_delete_ad_queue, name='ads_queue_bulk_delete'),
    path('ads/submit/', submit_pending_campaigns, name='ads_campaign_submit'),
]
