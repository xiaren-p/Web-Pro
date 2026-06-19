# Nextcloud 文件夹树

「系统 → Nextcloud」在系统内浏览与管理 Nextcloud 的文件夹树，并配置文件夹的访问权限规则。后端端点前缀 `/api/v1/nc/folder-tree`。

## 页面入口

侧边栏：系统 → Nextcloud（路由 `/system/nc`）。

## 功能说明

### 文件夹树浏览

`FolderTree` 以树形展示 Nextcloud 目录结构，可展开浏览子文件夹。

### 新建文件夹

在指定节点下创建子目录（`POST /nc/folder-tree/mkdir`）。

### 删除文件夹

删除前预览影响（`folder-delete-preview`），提示将影响的子目录与文件。确认后删除。

> 删除文件夹是不可逆操作，务必先看预览确认影响范围。建议删除前先在 Nextcloud 中备份或迁移文件夹内的数据。

### 权限规则分配

为文件夹设置 Nextcloud 群组的访问规则（读 / 写 / 删除等）：

- 单条设置：`POST /nc/folder-tree/set-rule`。
- 批量设置：`POST /nc/folder-tree/set-rules-batch`。
- 删除规则：`DELETE /nc/folder-tree/delete-rule`。
- 查看路径规则：`GET /nc/folder-tree/path-rules`。

权限规则变更同步到 Nextcloud 后即时生效。

### 用户目录树

`GET /nc/folder-tree/user-tree`：展示当前用户有权的目录。

### 群组列表

`GET /nc/folder-tree/groups`：Nextcloud 群组列表。

## 与 Nextcloud 的关系

- 系统通过 `api_v1/services/nc/nc_api_client.py` 调用 Nextcloud REST API 完成目录操作。
- 用户与群组数据由 `nc_sync_tasks`（Celery，`celery` 队列）从 Nextcloud 定时同步到本地表（`nc_group` 等）：
  - `process_pending_nc_tasks`：每 30 秒处理待同步队列。
  - `retry_failed_nc_tasks`：每 5 分钟重试失败任务。
- 单点登录走 OIDC，见运维指南 `06-oidc-nc.md`。

## NC_VERIFY_SSL

- 内网自签名证书环境可设 `NC_VERIFY_SSL=false`。
- **生产环境务必 `true`**。
