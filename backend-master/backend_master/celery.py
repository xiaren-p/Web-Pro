"""Celery 应用配置（celery.py）。

启动命令：
    # Worker
    celery -A backend_master worker -l info -Q default -c 2
    # Beat（定时任务调度）
    celery -A backend_master beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_master.settings")

app = Celery("backend_master")

# 从 Django settings 中读取 CELERY_ 前缀的配置
app.config_from_object("django.conf:settings", namespace="CELERY")

# 自动发现所有已安装 app 中的 tasks 模块
app.autodiscover_tasks()
