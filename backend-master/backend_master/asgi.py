"""
backend_master 项目的ASGI配置。
它将ASGI可调用对象作为名为“application”的模块级变量公开。
有关此文件的更多信息，请参阅
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_master.settings')

application = get_asgi_application()
