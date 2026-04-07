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
    ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost']),
    CORS_ALLOW_ALL_ORIGINS=(bool, True),
    CSRF_TRUSTED_ORIGINS=(list, ['http://localhost:3000', 'http://127.0.0.1:3000']),
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
    # 图片同步服务地址
    IMAGE_SYNC_URL=(str, 'https://cloud.hanlis.cn:9898'),
    # 高德天气 API 配置
    AMAP_BASE=(str,'https://restapi.amap.com'),
    AMAP_KEY=(str, '9ca18a1d97d6a8c31a77e001bfbd2742'),
    AMAP_CITY=(str, '440605'),  # 默认佛山南海区
    # LingXing OpenAPI SDK 配置
    LINGXING_SDK_APP_ID=(str, 'ak_cWhLzGDgtJ87v'),
    LINGXING_SDK_APP_SECRET=(str, 'AZ6veZryDpIkbH8HcGCG1w=='),
    LINGXING_SDK_API_BASE_URL=(str, 'https://openapi.lingxing.com'),
    # 可选：向外请求时使用的代理（JSON 字符串），例如: '{"http": "http://user:pass@host:port", "https": "http://..."}'
    LINGXING_SDK_PROXIES=(str, ''),
    # 是否让 aiohttp 使用环境变量中的代理（trust_env=True）
    LINGXING_SDK_TRUST_ENV=(bool, False),
    # 是否允许使用万能验证码绕过（仅用于受控开发/测试，生产请勿启用）
    ALLOW_CAPTCHA_BYPASS=(bool, False),
    # 全局万能验证码（仅在 ALLOW_CAPTCHA_BYPASS 为 true 时生效），请在生产环境不要设置
    CAPTCHA_MASTER_CODE=(str, ''),
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

# LingXing OpenAPI SDK 配置（可通过环境变量或 .env 文件设置）
LINGXING_SDK_APP_ID = env('LINGXING_SDK_APP_ID')
LINGXING_SDK_APP_SECRET = env('LINGXING_SDK_APP_SECRET')
LINGXING_SDK_API_BASE_URL = env('LINGXING_SDK_API_BASE_URL')
# 解析可选的代理配置（期望为 JSON 字符串或空）
LINGXING_SDK_PROXIES_RAW = env('LINGXING_SDK_PROXIES')
try:
    LINGXING_SDK_PROXIES = json.loads(LINGXING_SDK_PROXIES_RAW) if LINGXING_SDK_PROXIES_RAW else {}
except Exception:
    LINGXING_SDK_PROXIES = {}

LINGXING_SDK_TRUST_ENV = env('LINGXING_SDK_TRUST_ENV')

_allowed_from_env = os.environ.get('DJANGO_ALLOWED_HOSTS')
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
    'api_v1',              # 业务接口 v1
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend_master.wsgi.application'
ASGI_APPLICATION = 'backend_master.asgi.application'


# 数据库（开发默认 SQLite，后续可切换至 MySQL/PostgreSQL）

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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
STATIC_URL = 'static/'

# 媒体文件（文件上传）
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 默认主键类型

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 默认头像（用户未上传头像时使用）。可根据需要替换为 CDN/OSS 地址。
DEFAULT_AVATAR_URL = 'https://foruda.gitee.com/images/1723603502796844527/03cdca2a_716974.gif'

# 对外可访问的后端 URL（例如内部开发机对局域网可见的 IP）
BACKEND_EXTERNAL_URL = env('BACKEND_EXTERNAL_URL')
ONLINE_STALE_SECONDS = env('ONLINE_STALE_SECONDS')
# 是否允许 Django 在非 DEBUG 模式下通过视图直接提供媒体文件（仅在你确知需要 nginx 反代到 Django 时开启）
# 该变量在 urls.py 中通过 getattr(settings, 'DJANGO_SERVE_MEDIA', False) 读取
DJANGO_SERVE_MEDIA = env('DJANGO_SERVE_MEDIA')

# CORS（开发环境）
CORS_ALLOW_ALL_ORIGINS = env('CORS_ALLOW_ALL_ORIGINS')  # 生产建议改为 CORS_ALLOWED_ORIGINS 精确白名单
CORS_ALLOW_CREDENTIALS = True
# 允许的自定义请求头（包含 Authorization，便于携带令牌）
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
# 暴露的响应头（文件下载场景需要）
CORS_EXPOSE_HEADERS = [
    'Content-Disposition',
]

# 信任本地前端域名（CSRF）
CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')
if isinstance(CSRF_TRUSTED_ORIGINS, list):
    # 自动补充常见本地/局域网前端地址
    extra_origins = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://192.168.0.28:3000',
        'http://192.168.0.251:3000',
        'http://192.168.1.100:3000',
        'http://192.168.1.101:3000',
    ]
    for origin in extra_origins:
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

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

