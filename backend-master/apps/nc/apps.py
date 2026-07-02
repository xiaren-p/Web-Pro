from django.apps import AppConfig


class NcConfig(AppConfig):
    """Nc 应用配置。"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.nc"
    verbose_name = "Nextcloud 集成"
