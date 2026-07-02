from django.apps import AppConfig


class AiConfig(AppConfig):
    """Ai 应用配置。"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI 助手"
