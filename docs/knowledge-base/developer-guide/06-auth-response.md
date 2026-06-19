# 鉴权与统一响应

## 鉴权方式

### 前端用户：Bearer Token

- DRF 仅配置 `api_v1.auth.BearerTokenAuthentication`（自定义，基于 `AuthToken` 模型）。
- SessionAuthentication 已从 DRF 移除：OIDC SSO 走 Django 模板视图，不经过 DRF。保留 SessionAuthentication 会导致 Bearer 过期而 sessionid cookie 仍有效时，DRF 退化为 Session 鉴权并强制 CSRF 校验。
- 登录返回 `access_token` / `refresh_token`，有效期由 `.env` 的 `ACCESS_TOKEN_EXPIRE_SECONDS` / `REFRESH_TOKEN_EXPIRE_SECONDS` 控制。
- 前端通过 Axios 请求拦截器注入 `Authorization: Bearer <token>`。

### 外部应用：OAuth2 Client Credentials

- 通过 `/o/token/` 以 `grant_type=client_credentials` 获取 token，scope `api_v2`。
- 用于调 `api_v2` 工作流接口。
- 应用在「开发者设置 → 应用」管理，`client_secret` 明文存储（内网部署，便于排查 `invalid_client`）。

### Nextcloud 单点登录：OIDC

- 走 OIDC Authorization Code Flow，由 `oauth2_provider` 提供 `/o/authorize/`、`/o/token/`、`/o/userinfo/`。
- 登录页是 Django 模板视图 `/accounts/login/`，不经过 DRF。
- RSA 私钥文件 `backend_master/oidc_private.pem`，不存在时 OIDC 自动关闭。
- 自定义验证器 `api_v1.services.oidc.oidc_validator.CustomOAuth2Validator` 添加 NC 业务声明。
- `CLIENT_SECRET_HASHED=False`：变更后需重新执行 `setup_nc_oidc_client --reset-secret`。

## 权限

- DRF 默认 `IsAuthenticated`。
- `api_v1.permissions.menu_perm_required`：基于菜单 `perms` 字段的权限校验。
- `api_v2.permissions.workflow_permission.IsV2Accessible`：v2 接口访问权限。

## 统一响应格式

### 成功

```json
{ "code": "00000", "data": <任意>, "msg": "成功" }
```

### 分页

```json
{ "code": "00000", "data": { "total": 100, "list": [...] }, "msg": "成功" }
```

### 异常

异常经 `api_v1.utils.responses.custom_exception_handler` 统一处理，返回与成功一致的 `{code, data, msg}` 结构，HTTP 状态码仍遵循 DRF 约定（400/401/403/404/500）。

### 任务忙（409）

```json
{ "code": "B0001", "data": null, "msg": "xxx 任务正在执行中" }
```

由 `BUSY_RESPONSE` 生成，前端统一处理。

## CORS

- 开发环境 `CORS_ALLOW_ALL_ORIGINS=True`。
- 生产通过 `.env` 的 `CORS_ALLOWED_ORIGINS`（逗号分隔）配置白名单。
- `CORS_ALLOW_CREDENTIALS=True`。

## CSRF

- DRF 走 Bearer 不需要 CSRF。
- Django Admin / OIDC 登录页走 Session，需要 CSRF；`CSRF_TRUSTED_ORIGINS` 通过 `.env` 配置。
