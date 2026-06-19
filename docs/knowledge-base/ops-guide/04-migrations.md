# 数据库迁移

## 规则（CLAUDE.md §1.8）

- **迁移文件不上传 Git**：本地 `makemigrations` 生成的 `xxxx_*.py` 仅用于开发验证，生产由运维在服务器手动执行。
- **commit 只含 Model 文件**，不含迁移文件。
- **AI 无权在服务器执行** `makemigrations` / `migrate`，只能给出命令让运维手动执行。

> 历史遗留：Git 当前仍追踪 134 个历史迁移文件（截至 2026-06-16），未被 `.gitignore` 排除，与「不上传」规则不符；经确认保持现状，仅约束未来——后续 Model 变更勿再提交迁移文件。

## 开发端流程

1. 修改 Model（字段 / 索引 / 约束 / `choices` / `Meta`）。
2. 本地验证：

```bash
cd backend-master
python manage.py makemigrations
python manage.py migrate
```

3. 确认迁移文件可正确生成并已落库。
4. commit 只提交 Model 文件，**不提交**生成的迁移文件。
5. 给出服务器端迁移命令（见下）。

## 服务器端执行步骤

AI 改动 Model 后必须给出以下命令让运维手动执行：

```bash
# 1. 拉取最新代码（只含 Model 文件）
git pull

# 2. 生成迁移文件（让服务器自行生成）
python manage.py makemigrations

# 3. 应用迁移
python manage.py migrate
```

## 迁移冲突补救

### 同号分叉

本地与生产端迁移链不对齐时，先 `git pull` 同步生产端迁移文件，再 `makemigrations`，确保新迁移 `dependencies` 挂在正确节点。

### MySQL 不支持条件约束 / 表已存在

```bash
# 标记某迁移已应用而不真正执行
python manage.py migrate <app> <migration_name> --fake

# 或回滚到某个节点
python manage.py migrate <app> <target_migration>
```

### 手动 SQL

`managed=False` 的表（领星同步只读表）Django 不自动建表，需手动 SQL 建表，参考 `scripts/` 下的 SQL 脚本（如 `create_lx_exchange_rate.sql`）。

## 双数据库注意

- `analytics`（Doris）库由 `AnalyticsDatabaseRouter` 阻止迁移，`migrate` 不会对其执行。
- 迁移仅作用于 `default`（MySQL）。

## 迁移链对齐前置检查

生成新迁移前，必须先确认本地与生产端的迁移链是否对齐（对比最新 migration 文件名 / 编号）。若不对齐，先 `git pull` 同步，再 `makemigrations`，避免同号分叉或孤儿 merge 文件。
