"""
Django 配置（backend_master）

要点：
- 开发环境下启用 CORS 方便前后端联调；
- 使用 DRF 作为 API 框架，解析 JSON/Form/Multipart；
- 统一响应与分页在视图层封装，保持 {code,data,msg} 与 {total,list}；
- 使用 django-environ 读取 .env 配置，便于不同环境切换。
"""

from pathlib import Path
import os
import environ
import json

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ---- Env settings ----
env = environ.Env(
    DEBUG=(bool, True),
    SECRET_KEY=(str, 'django-insecure-v9t&lx8patv5db$l)y#4jioqhrvzzl!cg6k4grcn2ow0%+jd^r'),
    DJANGO_ALLOWED_HOSTS=(str, ''),  # 逗号分隔，优先于 ALLOWED_HOSTS 列表
    ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost']),
    CORS_ALLOW_ALL_ORIGINS=(bool, True),
    CORS_ALLOWED_ORIGINS=(str, ''),  # 逗号分隔，CORS_ALLOW_ALL_ORIGINS=False 时生效
    CSRF_TRUSTED_ORIGINS=(str, ''),  # 逗号分隔，空则为空列表
    ACCESS_TOKEN_EXPIRE_SECONDS=(int, 3600),
    REFRESH_TOKEN_EXPIRE_SECONDS=(int, 3600 * 24 * 7),
    # 可选：对外可访问的后端基础 URL（例如 http://192.168.0.251:8000），用于在 API 中生成对外可访问的绝对文件 URL
    BACKEND_EXTERNAL_URL=(str, ''),
    # WebSocket 使用的 Redis 通道层地址（未配置则使用内存层，仅适合开发单进程）
    REDIS_URL=(str, ''),
    # 在线用户心跳过期秒数（超过该秒数未 ping 视为离线）
    ONLINE_STALE_SECONDS=(int, 180),
    # 是否允许 Django 在非 DEBUG 模式下通过视图直接提供媒体文件（仅在你确知需要 nginx 反代到 Django 时开启）
    DJANGO_SERVE_MEDIA=(bool, False),
    # 默认头像
    DEFAULT_AVATAR_URL=(str, 'https://foruda.gitee.com/images/1723603502796844527/03cdca2a_716974.gif'),
    # 图片同步服务地址
    IMAGE_SYNC_URL=(str, 'https://cloud.hanlis.cn:9898'),
    # 高德天气 API 配置
    AMAP_BASE=(str, 'https://restapi.amap.com'),
    AMAP_KEY=(str, '9ca18a1d97d6a8c31a77e001bfbd2742'),
    AMAP_CITY=(str, '440605'),  # 默认佛山南海区
    # 是否允许使用万能验证码绕过（仅用于受控开发/测试，生产请勿启用）
    ALLOW_CAPTCHA_BYPASS=(bool, False),
    # 全局万能验证码（仅在 ALLOW_CAPTCHA_BYPASS 为 true 时生效），请在生产环境不要设置
    CAPTCHA_MASTER_CODE=(str, ''),
    # 安全响应头（开发默认全部关闭）
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    # Nextcloud 集成
    # NC_VERIFY_SSL=false 仅在内网自签名证书环境下使用；生产环境务必改为 true
    NC_VERIFY_SSL=(bool, False),
    # Fernet 对称加密密钥（用于 Config PASSWORD 类型值加密存储）
    # 生成命令：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_SECRET_KEY=(str, ''),
    # Celery Broker（复用 REDIS_URL；也可单独指定 CELERY_BROKER_URL）
    CELERY_BROKER_URL=(str, ''),
)

env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)


# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')
# 图片信息存储地址
IMAGE_SYNC_URL = env('IMAGE_SYNC_URL')
AMAP_BASE = env('AMAP_BASE')
AMAP_KEY = env('AMAP_KEY')
AMAP_CITY = env('AMAP_CITY')
# Nextcloud 集成配置
NC_VERIFY_SSL = env('NC_VERIFY_SSL')
FERNET_SECRET_KEY = env('FERNET_SECRET_KEY')

# Celery 配置
_celery_broker = env('CELERY_BROKER_URL') or (REDIS_URL if False else env('REDIS_URL'))
CELERY_BROKER_URL = _celery_broker or 'redis://127.0.0.1:6379/1'
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_BEAT_SCHEDULE = {
    # NC 同步：每 30 秒处理一次 PENDING 队列
    'nc-process-pending': {
        'task': 'api_v1.tasks.nc_sync_tasks.process_pending_nc_tasks',
        'schedule': 30.0,
    },
    # NC 同步：每 5 分钟将可重试的 FAILED 任务重置为 PENDING
    'nc-retry-failed': {
        'task': 'api_v1.tasks.nc_sync_tasks.retry_failed_nc_tasks',
        'schedule': 300.0,
    },
}

_allowed_from_env = os.environ.get('DJANGO_ALLOWED_HOSTS') or env('DJANGO_ALLOWED_HOSTS')
if _allowed_from_env:
    # 支持逗号分隔的字符串，例如: 'example.com,www.example.com'
    ALLOWED_HOSTS = [h.strip() for h in _allowed_from_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = env('ALLOWED_HOSTS')


# 应用定义

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',      # DRF
    'corsheaders',         # CORS（开发）
    'django_celery_results',  # Celery 任务结果存储
    'django_celery_beat',     # Celery 定时任务
    'oauth2_provider',        # OIDC Provider（django-oauth-toolkit）
    'api_v1',              # 业务接口 v1
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # 静态文件（nginx 前置时可移除）
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # 必须置于 CommonMiddleware 之前
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 操作日志中间件已移除：改为在需要时使用专门的事件或手动记录，以便后续大改造
]

ROOT_URLCONF = 'backend_master.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend_master.wsgi.application'
ASGI_APPLICATION = 'backend_master.asgi.application'


# 数据库（通过 .env 切换引擎，本地开发默认 MySQL，生产可改为 PostgreSQL 等）

_db_engine = env('DB_ENGINE', default='django.db.backends.mysql')

# MySQL 专属连接选项（其他引擎不需要）
_db_options = {}
if 'mysql' in _db_engine:
    _db_options = {
        'charset': 'utf8mb4',
        'connect_timeout': 10,
    }

DATABASES = {
    'default': {
        'ENGINE':   _db_engine,
        'NAME':     env('DB_NAME',     default='webpro_db'),
        'USER':     env('DB_USER',     default='root'),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST':     env('DB_HOST',     default='127.0.0.1'),
        'PORT':     env('DB_PORT',     default='3306'),
        'OPTIONS':  _db_options,
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# 国际化
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# 静态文件
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 媒体文件（文件上传）
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 默认主键类型

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DEFAULT_AVATAR_URL = env('DEFAULT_AVATAR_URL')

# 对外可访问的后端 URL（例如内部开发机对局域网可见的 IP）
BACKEND_EXTERNAL_URL = env('BACKEND_EXTERNAL_URL')
ONLINE_STALE_SECONDS = env('ONLINE_STALE_SECONDS')
# 是否允许 Django 在非 DEBUG 模式下通过视图直接提供媒体文件（仅在你确知需要 nginx 反代到 Django 时开启）
# 该变量在 urls.py 中通过 getattr(settings, 'DJANGO_SERVE_MEDIA', False) 读取
DJANGO_SERVE_MEDIA = env('DJANGO_SERVE_MEDIA')

# CORS
CORS_ALLOW_ALL_ORIGINS = env('CORS_ALLOW_ALL_ORIGINS')
if not CORS_ALLOW_ALL_ORIGINS:
    _cors_origins = env('CORS_ALLOWED_ORIGINS')
    CORS_ALLOWED_ORIGINS = [u.strip() for u in _cors_origins.split(',') if u.strip()] if _cors_origins else []
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_EXPOSE_HEADERS = ['Content-Disposition']

# CSRF
_csrf_env = env('CSRF_TRUSTED_ORIGINS')
CSRF_TRUSTED_ORIGINS = [u.strip() for u in _csrf_env.split(',') if u.strip()] if _csrf_env else []

# DRF 设置（解析器）。分页/响应统一在视图内封装。
REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api_v1.auth.BearerTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'EXCEPTION_HANDLER': 'api_v1.utils.responses.custom_exception_handler',
}

# 认证令牌有效期（秒）
ACCESS_TOKEN_EXPIRE_SECONDS = env('ACCESS_TOKEN_EXPIRE_SECONDS')
REFRESH_TOKEN_EXPIRE_SECONDS = env('REFRESH_TOKEN_EXPIRE_SECONDS')

# 图片验证码万能口令配置（仅用于开发/测试）
ALLOW_CAPTCHA_BYPASS = env('ALLOW_CAPTCHA_BYPASS')
CAPTCHA_MASTER_CODE = env('CAPTCHA_MASTER_CODE') or None
# 安全提示：若在非 DEBUG 环境启用了万能口令，发出警告以提醒审计
if ALLOW_CAPTCHA_BYPASS and not DEBUG:
    import warnings
    warnings.warn("ALLOW_CAPTCHA_BYPASS is enabled in non-debug mode; this is insecure and should not be used in production.", RuntimeWarning)

# 文件管理模块已下线；如需恢复请参考历史提交

# Channels 已从项目中移除；保留 REDIS_URL 以备将来需要，但不再配置 CHANNEL_LAYERS
REDIS_URL = env('REDIS_URL')

# 缓存配置：若提供 REDIS_URL 则使用 django-redis 的 RedisCache，否则使用默认 locmem
try:
    if REDIS_URL:
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': REDIS_URL,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                }
            }
        }
except Exception:
    pass

# 安全响应头（开发默认全部关闭，生产通过 .env 开启）
SECURE_SSL_REDIRECT = env('SECURE_SSL_REDIRECT')
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE')
CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE')
# OIDC SSO 跨站 Session：NC 开启 SSO 时浏览器从 NC 域跳到 api.hanlis.cn，
# SameSite=None 才能在该跳转请求中自动携带 sessionid cookie。
# 必须配合 SESSION_COOKIE_SECURE=True（HTTPS）一起使用。
SESSION_COOKIE_SAMESITE = 'None'
SECURE_HSTS_SECONDS = env('SECURE_HSTS_SECONDS')
# 反向代理 HTTPS 透传：告知 Django 外层已是 HTTPS，修复 Admin CSRF 403
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# 日志
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'verbose': {'format': '[%(asctime)s] %(levelname)s %(name)s %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'}},
    'root': {'handlers': ['console'], 'level': LOG_LEVEL},
}

# ---- OIDC Provider（django-oauth-toolkit 3.x）----
# RSA 私鑰文件：不存在时 OIDC 功能自动关闭。
# 生成命令： python manage.py generate_oidc_key
_oidc_key_file = BASE_DIR / 'backend_master' / 'oidc_private.pem'
_oidc_rsa_private_key = _oidc_key_file.read_text(encoding='utf-8') if _oidc_key_file.exists() else ''

OAUTH2_PROVIDER = {
    # OIDC 启用开关：私鑰文件存在时才真正启用
    'OIDC_ENABLED': bool(_oidc_rsa_private_key),
    'OIDC_RSA_PRIVATE_KEY': _oidc_rsa_private_key,
    # ID Token 有效期 1 小时
    'ID_TOKEN_EXPIRE_SECONDS': 3600,
    # 授权码有效期 60 秒
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 60,
    # 支持的 Scope
    'SCOPES': {
        'openid': 'OpenID Connect 标识',
        'profile': '个人资料（名称、手机号、群组、管理员标志）',
        'email': '邮符1地址',
        'phone': '手机号',
        'groups': 'Nextcloud 群组成员关系',
    },
    'DEFAULT_SCOPES': ['openid', 'profile', 'email'],
    # 请求 scope 验证：请求的 scope 必须是 SCOPES 的子集
    'REQUEST_APPROVAL_PROMPT': 'auto',
    # 自定义验证器（添加 NC 业务声明）
    'OAUTH2_VALIDATOR_CLASS': 'api_v1.services.oidc.oidc_validator.CustomOAuth2Validator',
    # 支持的授权类型
    'ALLOWED_GRANT_TYPES': [
        'authorization_code',
        'implicit',
        'password',
        'client_credentials',
        'refresh_token',
        'openid_hybrid',
    ],
    # NC user_oidc 不必须 PKCE，内网环境可以不强制
    'PKCE_REQUIRED': False,
}

