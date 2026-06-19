# 数据库（双库）

系统使用双数据库，由 `backend_master/analytics_database_router.AnalyticsDatabaseRouter` 路由。

## 双库说明

| 别名 | 引擎 | 用途 | 迁移 |
| --- | --- | --- | --- |
| `default` | MySQL | 业务读写 | Django 迁移管理 |
| `analytics` | Apache Doris | 只读分析（聚合查询） | 路由器阻止 Django 迁移 |

## 路由器行为

`AnalyticsDatabaseRouter`：

- `db_for_read` / `db_for_write`：根据 app label 判断路由到哪个库。
- `allow_migrate`：`analytics` 库返回 `False`，阻止 Django 对 Doris 执行迁移；其余返回 `None` 交给默认逻辑。
- Doris 只作为只读分析库参与聚合查询，业务写入与迁移职责全在 MySQL。

## 配置

数据库连接通过 `.env` 配置：

```bash
# MySQL（业务）
DB_ENGINE=django.db.backends.mysql
DB_NAME=webpro_db
DB_USER=<YOUR_DB_USER>
DB_PASSWORD=<YOUR_DB_PASSWORD>
DB_HOST=127.0.0.1
DB_PORT=3306

# Doris（分析）
DORIS_DB_NAME=webpro_db
DORIS_DB_USER=<YOUR_DORIS_USER>
DORIS_DB_PASSWORD=<YOUR_DORIS_PASSWORD>
DORIS_DB_HOST=127.0.0.1
DORIS_DB_PORT=9030
```

MySQL 连接选项：`charset=utf8mb4`、`connect_timeout=10`、`CONN_MAX_AGE=600`。

## Doris 自定义后端

`backend_master/doris_backend/` 是自定义数据库后端，适配 Doris 的 SQL 方言与连接方式。

## 模型与 `managed=False`

领星同步的只读表（`lx_*` 系列）多为 `managed=False`，Django 不管理其表结构，由领星同步或手动 SQL 建表。这类模型的 `Meta` 必须显式 `managed = False` + `db_table`。

## 迁移规则

- 迁移文件**不上传** Git（CLAUDE.md §1.8），本地 `makemigrations` 仅用于开发验证，生产由运维在服务器手动执行。
- AI 改动 Model 后必须给出服务器端 `makemigrations` + `migrate` 步骤。
- `analytics` 库不参与迁移，路由器已阻止。
