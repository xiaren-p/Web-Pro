from django.apps import AppConfig


class NoticeConfig(AppConfig):
    """Notice 应用配置。"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notice"
    verbose_name = "通知公告"
