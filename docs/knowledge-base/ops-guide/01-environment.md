# 环境变量

后端通过 `django-environ` 读取 `backend-master/.env`（被 gitignore，必需，缺失则服务起不来）。本文列出全部环境变量。

## 数据库

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DB_ENGINE` | `django.db.backends.mysql` | 业务库引擎 |
| `DB_NAME` | `webpro_db` | 业务库名 |
| `DB_USER` | `root` | 业务库用户 |
| `DB_PASSWORD` | （空） | 业务库密码 |
| `DB_HOST` | `127.0.0.1` | 业务库主机 |
| `DB_PORT` | `3306` | 业务库端口 |
| `DORIS_DB_NAME` | `webpro_db` | Doris 库名 |
| `DORIS_DB_USER` | `root` | Doris 用户 |
| `DORIS_DB_PASSWORD` | （空） | Doris 密码 |
| `DORIS_DB_HOST` | `127.0.0.1` | Doris 主机 |
| `DORIS_DB_PORT` | `9030` | Doris 端口 |

## Redis 与 Celery

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `REDIS_URL` | （空） | Redis 地址，未配置则缓存用 locmem、Celery broker 回退 `redis://127.0.0.1:6379/1` |
| `CELERY_BROKER_URL` | （空） | 可单独指定，否则复用 `REDIS_URL` |

## 安全与密钥

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | 内置 insecure | Django 密钥，生产必须替换 |
| `FERNET_SECRET_KEY` | （空） | Fernet 对称加密密钥，Config PASSWORD 类型必需。生成：`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DIFY_API_BASE` | （空） | Dify 平台 base URL |
| `DIFY_API_KEY` | （空） | Dify 应用 sk- 密钥，仅后端读取 |

## 鉴权与 Token

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | `3600` | access token 有效期 |
| `REFRESH_TOKEN_EXPIRE_SECONDS` | `2592000` | refresh token 有效期（30 天） |
| `ALLOW_CAPTCHA_BYPASS` | `False` | 万能验证码开关，生产禁用 |
| `CAPTCHA_MASTER_CODE` | （空） | 万能验证码，仅 `ALLOW_CAPTCHA_BYPASS=True` 生效 |

## Web 与 CORS

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DEBUG` | `True` | 调试模式，生产必须 `False` |
| `DJANGO_ALLOWED_HOSTS` | （空） | 逗号分隔，优先于 `ALLOWED_HOSTS` |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | 允许的主机 |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | 开发全开，生产改 `False` + `CORS_ALLOWED_ORIGINS` |
| `CORS_ALLOWED_ORIGINS` | （空） | 逗号分隔的来源白名单 |
| `CSRF_TRUSTED_ORIGINS` | （空） | 逗号分隔，Django Admin / OIDC 登录页需要 |
| `BACKEND_EXTERNAL_URL` | （空） | 对外可访问的后端 URL，用于生成绝对文件 URL |
| `DJANGO_SERVE_MEDIA` | `True` | 非 DEBUG 下是否由 Django 直接提供媒体文件 |

## 安全响应头

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `SECURE_SSL_REDIRECT` | `False` | 强制 HTTPS 跳转 |
| `SESSION_COOKIE_SECURE` | `False` | cookie 仅 HTTPS |
| `CSRF_COOKIE_SECURE` | `False` | CSRF cookie 仅 HTTPS |
| `SECURE_HSTS_SECONDS` | `0` | HSTS 时长 |

## Nextcloud 与业务集成

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `NC_VERIFY_SSL` | `False` | NC HTTPS 证书校验，内网自签名可关，生产务必 `True` |
| `IMAGE_SYNC_URL` | `https://cloud.hanlis.cn:9898` | 图片同步服务地址 |
| `AMAP_BASE` | `https://restapi.amap.com` | 高德天气 API base |
| `AMAP_KEY` | 内置 | 高德 Key |
| `AMAP_CITY` | `440605` | 默认城市（佛山南海区） |
| `DEFAULT_AVATAR_URL` | （空） | 默认头像兜底 URL，空则前端用本地占位图 |
| `ONLINE_STALE_SECONDS` | `180` | 在线用户心跳过期秒数 |

## 前端环境变量（`vue3-element-admin-master/.env.development`）

| 变量 | 开发默认 | 说明 |
| --- | --- | --- |
| `VITE_APP_PORT` | `3000` | Vite 开发端口（未设回退 5173） |
| `VITE_APP_TITLE` | `vue3-element-admin` | 项目标题 |
| `VITE_APP_BASE_API` | `/dev-api` | 代理前缀 |
| `VITE_APP_API_URL` | `http://127.0.0.1:8000/api/v1` | 后端接口地址 |
| `VITE_APP_API_ORIGIN` | （空） | api_v2 / OAuth2 端点源站，开发留空走代理 |

## 安全提示

- `.env` 被 gitignore，禁止提交。
- 文档中真实密钥用 `<YOUR_xxx>` 替换。
- `DIFY_API_KEY` 严禁出现在前端代码或日志中。
