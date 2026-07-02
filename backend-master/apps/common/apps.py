from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Common 应用配置。"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "基础服务"
