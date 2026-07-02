"""AI 助手域 — URL 路由（v2 工作流部分）。"""

from django.urls import path

from apps.ai.views.task_view import cancel_workflow, get_workflow_status, start_workflow

urlpatterns = [
    path('workflow/', start_workflow, name='workflow_start'),
    path('workflow/<int:execution_id>/', get_workflow_status, name='workflow_status'),
    path('workflow/<int:execution_id>/cancel/', cancel_workflow, name='workflow_cancel'),
]
