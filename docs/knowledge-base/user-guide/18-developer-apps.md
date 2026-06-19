# 开发者应用管理

「开发者设置 → 应用」管理对外提供 OAuth2 Client Credentials 的应用，外部系统可凭此调 `api_v2` 工作流接口。后端端点前缀 `/api/v2/developer/apps`。

## 入口

侧边栏：开发者设置 → 应用（路由 `/developer/apps`）。

## 应用列表

- 分页展示应用名称、Client ID、Scope、状态、创建时间。
- Scope 固定为 `api_v2`（工作流任务接口访问权限）。

## 新增应用

1. 点击「新增」，填写应用名。
2. 系统生成 `client_id` 与 `client_secret`，**secret 仅在创建时显示一次**，需立即保存。
3. `client_secret` 在数据库中明文存储（内网部署，DB 有防火墙保护），便于排查 `invalid_client`。

## 密钥轮换

- 单行「轮换密钥」（`POST /developer/apps/<id>/rotate-secret/`）生成新的 `client_secret`，旧密钥立即失效。
- 轮换后需同步更新外部系统的配置。

## 外部调用方式

外部应用获取访问令牌：

```bash
curl -X POST <后端地址>/o/token/ \
  -d "grant_type=client_credentials" \
  -d "client_id=<CLIENT_ID>" \
  -d "client_secret=<CLIENT_SECRET>" \
  -d "scope=api_v2"
```

拿到 `access_token` 后，以 `Authorization: Bearer <token>` 调 `api_v2` 接口（如 `/api/v2/workflow/`）。

## 支持的 Scope

| Scope | 说明 |
| --- | --- |
| `openid` | OIDC 标识 |
| `profile` | 个人资料 |
| `email` | 邮箱 |
| `phone` | 手机号 |
| `groups` | Nextcloud 群组成员关系 |
| `api_v2` | API v2 接口访问权限（Client Credentials 外部调用） |

## 安全提示

- `client_secret` 属于敏感凭据，严禁出现在前端代码或日志中。
- 不再使用的应用应及时删除。
- `CLIENT_SECRET_HASHED=False`：明文存储，变更后需重新执行 `setup_nc_oidc_client --reset-secret`。
