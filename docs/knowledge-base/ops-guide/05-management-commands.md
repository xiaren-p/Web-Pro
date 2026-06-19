# 管理命令

所有命令在 `backend-master/` 下执行：`python manage.py <命令>`。

## 菜单与权限

| 命令 | 说明 |
| --- | --- |
| `sync_system_menus` | 同步系统菜单与按钮权限，清理历史残留。部署或菜单变更后执行。 |
| `grant_admin_system_perms` | 授予管理员系统全部权限 |
| `find_menu_perms` | 按权限 token 子串查找菜单（排查权限点） |

## OIDC 与 Nextcloud

| 命令 | 说明 |
| --- | --- |
| `generate_oidc_key` | 生成 OIDC RSA 私钥（`backend_master/oidc_private.pem`），不存在时 OIDC 自动关闭 |
| `setup_nc_oidc_client` | 为 Nextcloud user_oidc 注册 OAuth Client；`--reset-secret` 重置密钥（变更 `CLIENT_SECRET_HASHED` 后必须执行） |
| `reconcile_nc` | Nextcloud 全量对账（首次迁移、NC 故障恢复后、人工排查不一致时用） |
| `sync_nc_avatars` | 批量同步用户头像到 NC（用户级凭据） |
| `reset_user_avatars` | 为所有用户随机重分配预设头像并实时同步到 NC |

## 数据维护

| 命令 | 说明 |
| --- | --- |
| `audit_orphans` | 审计潜在孤立外键，整体数据健康度快速检查 |
| `cleanup_orphan_uploads` | 扫描上传目录，清理超期且未被引用的孤儿文件 |
| `purge_file_module_artifacts` | 清理文件模块遗留菜单与角色关联；`--with-logs` 额外清理历史操作日志中文件相关记录 |
| `prune_orderprofitcache` | 清理超 TTL 的 OrderProfitCache；`--minutes N` 指定阈值，`--dry-run` 预览 |

## 调试与排查

| 命令 | 说明 |
| --- | --- |
| `print_recent_logs` | 打印最近操作日志（带耗时），`--limit N` 控制条数 |
| `inspect_notices` | 检查通知并打印样本序列化输出 |

## 初始化

| 命令 | 说明 |
| --- | --- |
| `bootstrap_demo` | 初始化最小演示数据 |

## 文件模块下线相关

原「文件管理」模块已下线，升级时执行：

```bash
python manage.py migrate
python manage.py sync_system_menus
python manage.py purge_file_module_artifacts --with-logs
python manage.py audit_orphans
```
