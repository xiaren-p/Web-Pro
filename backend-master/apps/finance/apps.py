from django.apps import AppConfig


class FinanceConfig(AppConfig):
    """Finance 应用配置。"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    verbose_name = "财务管理"
