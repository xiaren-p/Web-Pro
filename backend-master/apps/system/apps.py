from django.apps import AppConfig

class SystemConfig(AppConfig):
    """System 应用配置。"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.system"
    verbose_name = "系统管理"
