from django.apps import AppConfig


class AdsConfig(AppConfig):
    """Ads 应用配置。"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ads"
    verbose_name = "广告管理"
