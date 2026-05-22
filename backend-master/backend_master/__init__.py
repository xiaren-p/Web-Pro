"""Celery 应用初始化。

在 Django 项目启动时自动加载，确保 Celery Beat 和 Worker 能正确发现任务。
"""
# 延迟导入避免 settings 尚未就绪时的循环初始化问题
default_app_config = "api_v1.apps.ApiV1Config"

try:
    from backend_master.celery import app as celery_app  # noqa: F401
    __all__ = ("celery_app",)
except Exception:
    pass
