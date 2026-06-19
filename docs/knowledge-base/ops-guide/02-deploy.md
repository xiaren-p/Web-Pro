# 部署与启动

## 后端（`backend-master/`）

### 前置条件

- Python 3.10+（Django 5.1 要求）
- MySQL 8（业务库）
- Apache Doris（分析库，可选，仅聚合查询需要）
- Redis（缓存 + Celery broker）
- `backend-master/.env` 已配置（见 `01-environment.md`）

### 安装依赖

```bash
cd backend-master
pip install -r requirements.txt
```

### 初始化

```bash
# 1. 生成数据库表（生产在服务器手动执行，见 04-migrations.md）
python manage.py makemigrations
python manage.py migrate

# 2. 同步系统菜单与按钮权限
python manage.py sync_system_menus

# 3. （可选）初始化演示数据
python manage.py bootstrap_demo
```

### 启动 Web

```bash
python manage.py runserver 0.0.0.0:8000
```

生产用 Gunicorn / uWSGI，命令以实际部署为准。

### ASGI（WebSocket / SSE）

AI 助手 SSE 订阅走 WSGI 同步生成器（`StreamingHttpResponse`），无需 ASGI。WebSocket（STOMP）如需启用走 ASGI：

```bash
daphne -b 0.0.0.0 -p 8000 backend_master.asgi:application
```

## 前端（`vue3-element-admin-master/`）

### 前置条件

- Node `^20.19.0 || >=22.12.0`
- pnpm（强制，`preinstall` 拦截 npm/yarn）

### 安装依赖

```bash
cd vue3-element-admin-master
pnpm install
```

### 开发启动

```bash
pnpm run dev
```

端口取自 `VITE_APP_PORT`（默认 3000），请求走 `/dev-api` 代理到后端。

### 生产构建

```bash
pnpm run build
```

产物在 `dist/`，由 nginx 托管并反代到后端。

## nginx 反代要点

- 前端静态：`/` → `dist/`。
- API：`/api/v1/`、`/api/v2/`、`/o/` → 后端。
- 媒体：`/media/` → 后端 `media/` 或对象存储。
- 兼容别名 `/prod-api/` → 后端 `api_v1`（见 `backend_master/urls.py`）。
- SSE：`X-Accel-Buffering: no`（AI 流式订阅必需，已在后端响应头设置，nginx 透传即可）。
- HTTPS：生产开启，配合 `SESSION_COOKIE_SECURE=True`、`SECURE_SSL_REDIRECT=True`。
