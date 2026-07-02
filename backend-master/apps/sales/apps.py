from django.apps import AppConfig


class SalesConfig(AppConfig):
    """Sales 应用配置。"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sales"
    verbose_name = "销售管理"
