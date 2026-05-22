"""Celery 异步任务包。"""
# 显式导入各任务模块，确保 autodiscover_tasks() 能注册到子包中的任务
from api_v1.tasks import nc_sync_tasks  # noqa: F401
