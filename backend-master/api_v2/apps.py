"""应用配置：`api_v2` 工作流任务调度模块的 Django AppConfig。"""

from django.apps import AppConfig


class ApiV2Config(AppConfig):
    """工作流任务调度模块应用配置。"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_v2'
    verbose_name = '任务调度 v2'
