"""应用配置：`api_v1` 的 Django AppConfig。

模块说明：此模块包含 `ApiV1Config`，在应用就绪时用于初始化第三方 SDK（如 LingXing
的 SyncTokenManager）。该初始化为可选项，若未配置相关环境变量则安全跳过。
"""

from django.apps import AppConfig
from django.conf import settings


class ApiV1Config(AppConfig):
    name = 'api_v1'

    def ready(self):
        """应用启动时初始化 LingXing SDK Token（在可用时启用后台自动刷新）。

        说明：该逻辑在 Django 启动（manage.py runserver / Gunicorn / Uvicorn）时运行。它会尝试初始化
        `SyncTokenManager`（在 openapi.sync_token_manager 中），并开启自动刷新，确保后端可以无感知访问 LingXing OpenAPI。
        """
        try:
            from openapi.sync_token_manager import SyncTokenManager
        except Exception:
            # 如果导入失败（例如不在 PYTHONPATH），则不阻塞启动
            return

        app_id = getattr(settings, 'LINGXING_SDK_APP_ID', None)
        app_secret = getattr(settings, 'LINGXING_SDK_APP_SECRET', None)
        host = getattr(settings, 'LINGXING_SDK_API_BASE_URL', None)

        if not (app_id and app_secret and host):
            # 未配置，不自动初始化
            return

        try:
            mgr = SyncTokenManager.get_instance(host=host, app_id=app_id, app_secret=app_secret)
            # 启动后台自动刷新，默认检查间隔 30s，安全提前量 60s
            mgr.start_auto_refresh(check_interval=30, safety_margin=60)
        except Exception:
            # 不要让初始化阻塞或导致应用崩溃
            pass
