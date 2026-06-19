# OIDC 与 Nextcloud 配置

## OIDC Provider（本系统作为身份提供者）

本系统通过 `django-oauth-toolkit` 提供 OIDC，Nextcloud 的 `user_oidc` 插件作为消费方实现 SSO。

### 前置条件

- RSA 私钥已生成：

```bash
python manage.py generate_oidc_key
```

生成 `backend_master/oidc_private.pem`，不存在时 OIDC 自动关闭。

### 注册 NC OAuth Client

```bash
python manage.py setup_nc_oidc_client
```

为 Nextcloud user_oidc 注册 OAuth Client。变更 `CLIENT_SECRET_HASHED=False` 后必须执行：

```bash
python manage.py setup_nc_oidc_client --reset-secret
```

### OIDC 端点

| 端点 | 说明 |
| --- | --- |
| `/o/authorize/` | 授权端点 |
| `/o/token/` | 令牌端点（Authorization Code / Client Credentials / Refresh Token） |
| `/o/userinfo/` | 用户信息端点 |
| `/.well-known/openid-configuration` | OIDC 发现配置 |
| `/accounts/login/` | 登录页（Django 模板视图，不经过 DRF） |

### 支持的 Scope

| Scope | 说明 |
| --- | --- |
| `openid` | OIDC 标识 |
| `profile` | 名称、手机号、群组、管理员标志 |
| `email` | 邮箱 |
| `phone` | 手机号 |
| `groups` | Nextcloud 群组成员关系 |
| `api_v2` | API v2 接口访问权限（Client Credentials 外部调用） |

### 关键配置

- `OIDC_ENABLED`：私钥存在时才启用。
- `CLIENT_SECRET_HASHED=False`：明文存储，便于排查 `invalid_client`。
- `PKCE_REQUIRED=False`：内网环境不强制。
- 自定义验证器：`api_v1.services.oidc.oidc_validator.CustomOAuth2Validator`（添加 NC 业务声明）。

## Nextcloud 集成

### 用户与群组同步

- `nc_sync_tasks`（Celery，`celery` 队列）定时从 NC 同步用户与群组到本地表（`nc_group` 等）。
- `process_pending_nc_tasks`：每 30 秒处理待同步队列。
- `retry_failed_nc_tasks`：每 5 分钟重试失败任务。

### 全量对账

```bash
python manage.py reconcile_nc
```

首次迁移、NC 故障恢复后、人工排查不一致时使用。

### 头像同步

```bash
python manage.py sync_nc_avatars      # 批量同步
python manage.py reset_user_avatars   # 重分配预设头像并同步
```

### NC API 客户端

`api_v1.services.nc.nc_api_client` 封装 Nextcloud REST API 调用。

### NC_VERIFY_SSL

- 内网自签名证书环境可设 `NC_VERIFY_SSL=false`。
- **生产环境务必 `true`**。

## SSO 跨站 Session

NC 开启 SSO 时浏览器从 NC 域跳到后端域，`SESSION_COOKIE_SAMESITE=None` 才能在跳转请求中自动携带 sessionid cookie。必须配合 `SESSION_COOKIE_SECURE=True`（HTTPS）一起使用。

## CSRF

OIDC 登录页走 Django Session，需要 CSRF。`CSRF_TRUSTED_ORIGINS` 通过 `.env` 配置（逗号分隔）。反代 HTTPS 透传已配置 `SECURE_PROXY_SSL_HEADER`，修复 Admin CSRF 403。
