# AGENTS.md

面向 OpenCode 会话的高密度工程备忘。仅收录"不看就会踩坑"的仓库专属事实；通用编程常识、语言默认规范不在此重复。

## 项目结构

单仓双应用，技术栈完全独立，互不依赖构建：

- `backend-master/` — Django 5.1 + DRF + Celery，入口 `backend_master/`（`settings.py` / `urls.py` / `celery.py`）。
- `vue3-element-admin-master/` — Vue 3 + Vite + TS + Element Plus + Pinia，入口 `src/main.ts`。
- 根 `tools/` 当前为空；`tests/` 目录不存在。

## 指令文件体系（重要）

- `CLAUDE.md`（根，**已纳入 Git**）是唯一随仓库分发的权威规范总纲，会被会话自动加载。所有详细架构与语言细则都在其中。
- `.github/copilot-instructions.md` 与 `.github/instructions/{python,frontend,markdown,architecture}.instructions.md` 是语言专属细则，**但 `.github/` 整体被 `.gitignore` 排除（0 个文件被追踪）**。全新 clone 的环境拿不到这些细则，只有 `CLAUDE.md`。需要细则时优先读 `CLAUDE.md`，缺失部分再参考本地 `.github/instructions/`。
- 规范冲突优先级见 `CLAUDE.md` 第八节；执行时以"可执行真相"为准（见下文"已知文档冲突"）。

## 前端命令与陷阱（`vue3-element-admin-master/`）

- **包管理器强制 pnpm**：`package.json` 的 `preinstall` 跑 `npx only-allow pnpm`，用 `npm` / `yarn` 安装会直接失败。Node 要求 `^20.19.0 || >=22.12.0`。
- 关键脚本（用 `pnpm run <name>` 或 `npm run <name>` 均可，但安装必须 pnpm）：
  - `dev` — Vite 开发服务器，端口取自 `VITE_APP_PORT`（`.env.development` 设为 3000，未设回退 5173）。
  - `type-check` — 类型检查命令是 `vue-tsc --noEmit`（**不是** `typecheck`）。
  - `lint` — 串联 `lint:eslint` + `lint:prettier` + `lint:stylelint`。
  - `build` — `vue-tsc --noEmit & vite build`。
- **提交钩子**：`pre-commit` 跑 `lint:lint-staged`（只校验暂存文件）；`commit-msg` 跑 `commitlint`，强制 Conventional Commits 且 **type 枚举自定义**：`feat|fix|docs|style|refactor|perf|test|build|ci|revert|chore|wip`。交互式提交用 `npm run commit`（commitizen）。
- 改动前端代码后，提交前至少跑 `pnpm run type-check` 与 `pnpm run lint:eslint`。

## 前端 API / 代理约定

- 开发态请求统一走 `/dev-api` 前缀（`VITE_APP_BASE_API=/dev-api`），由 `vite.config.ts` 的 proxy 重写后转发到 `VITE_APP_API_URL`（默认 `http://127.0.0.1:8000/api/v1`）。
- proxy 规则（`vite.config.ts` 内）：`/dev-api/media/*` → `/media/*`；`/dev-api/(api/v[2-9]|o)/` 仅剥前缀保留路径；其余 → `/api/v1`。
- 后端对应入口：`/api/v1/`、`/api/v2/`、OAuth2 `/o/`，另有 `/prod-api/` 兼容别名（见 `backend_master/urls.py`）。
- 前端所有网络请求必须经 `src/api/<板块>/` 封装，**禁止**在视图/组件里直接 `axios`/`fetch`。

## 后端命令与陷阱（`backend-master/`）

- 所有命令在 `backend-master/` 目录下执行，`DJANGO_SETTINGS_MODULE=backend_master.settings`。
- **`backend-master/.env` 被 gitignore 且必需**：`django-environ` 读取它，DB / `FERNET_SECRET_KEY` / `REDIS_URL` / `DIFY_API_KEY` / OIDC 私钥等均依赖此文件。没有 `.env` 服务起不来。
- 开发服务器：`python manage.py runserver`。
- **Celery worker 必须显式列出所有队列**，否则未列出的队列任务永远不执行：
  ```bash
  celery -A backend_master worker -l info -Q celery,parallel_queue,single_thread_queue
  ```
- Celery beat：`celery -A backend_master beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`。
- **后端无自动化测试套件**：`requirements.txt` 含 `pytest`，但仓库内无 `tests/`、无 `pytest.ini`/`pyproject.toml` 配置。验证靠 `runserver` 手动联调 + `vue-tsc`/`eslint`（前端）。不要假设存在 `pytest` / `tox` / `ruff` 命令。
- 自定义管理命令（`api_v1/management/commands/`）：`sync_system_menus`、`setup_nc_oidc_client`、`generate_oidc_key`、`purge_file_module_artifacts`、`audit_orphans`、`reconcile_nc` 等，部署/运维常用。

## Celery 任务新增清单（最高频踩坑点）

新增任务漏一步即"任务静默不执行"或"Received unregistered task"。必须按序完成：

1. 写任务文件 `api_v2/tasks/xxx_task.py`（或 `api_v1/tasks/`），`@shared_task` 的 `name=` 必须等于完整模块路径（如 `api_v2.tasks.xxx_task.run_xxx_task`），**禁止**在装饰器写 `queue=`。
2. 在 `api_v2/tasks/__init__.py`（或 `api_v1/tasks/__init__.py`）**显式 `import` 该任务并加入 `__all__`**——不注册则 worker 启动时不加载。
3. 在 `backend_master/settings.py` 的 `CELERY_TASK_ROUTES` 追加一行，key 与装饰器 `name` 一字不差；按决策树选队列：
   - `single_thread_queue`（concurrency=1）：须串行、写同资源、调有 QPS 限制的外部 API。
   - `parallel_queue`（concurrency=4）：可并发的批量/AI 任务。
   - `celery`（默认）：轻量、定时、低频。
4. 若为定时任务，在 `CELERY_BEAT_SCHEDULE` 追加项；**高频任务（schedule ≤ 60s）必须加 `options.expires` 且 < schedule**，防止 Beat 堆积。
5. **重启 Django Web**（路由表是 Django 派发时读的）+ **重启目标队列的 Celery worker**（worker 启动时才扫描 `tasks/__init__.py`）。

任务加锁统一用 `api_v2/utils/task_execution_lock.py`（`TaskExecutionLock` / `is_task_running` / `BUSY_RESPONSE`），三层防御与模板见 `CLAUDE.md` §5。视图禁止 `cache.add` 写锁，`LOCK_KEY` 必须从任务模块 `import` 复用。

## 架构约定（偏离默认，易被违反）

- **绝对路径导入**：后端 `from api_v1...` / `from api_v2...`，**禁止相对导入**；前端 `@/...` 别名，**禁止相对路径**。
- **一类一文件**：后端每个 Model / Serializer / View / Middleware / Permission / Auth / Service / Celery Task 一个 `.py`；前端每个 SFC / Store / Composable / API 模块一个文件，SFC ≤ 400 行。板块用同名子目录聚合（`api_v1/models/ads/`、`src/api/ads/` 等）。
- **数据出口最终成形**：枚举翻译、金额/日期/单位格式化、字段重命名、聚合统计必须在**后端** serializer/service 完成；前端拿到即可渲染，**禁止**在前端 `views`/`components`/`composables` 做业务字段重映射或格式化。
- **统一响应**：`{code, data, msg}`，成功 `code="00000"`；分页 `{total, list}`。异常经 `api_v1.utils.responses.custom_exception_handler` 统一处理。
- **鉴权**：DRF 仅 `api_v1.auth.BearerTokenAuthentication`，Session 认证已从 DRF 移除（OIDC SSO 走 Django 模板视图，不经过 DRF）。外部应用走 OAuth2 Client Credentials（`/o/token/`，scope `api_v2`）。
- **双数据库**：`default`（MySQL，业务）+ `analytics`（Doris，分析），由 `backend_master/analytics_database_router.AnalyticsDatabaseRouter` 路由。
- **命名/注释**：标识符全英文（禁拼音），类/函数文档与逻辑注释用**中文**；生产代码禁 `print()`/`console.log()`，走 Logger 且每条日志带 `[类名] [方法名]` 前缀，`ERROR` 带 `exc_info=True`。
- 前端 SFC 块顺序固定 `<template>` → `<script setup lang="ts">` → `<style scoped lang="scss">`；`defineProps`/`defineEmits` 带 TS 泛型。

## 已知文档冲突（以可执行真相为准）

- **数据库迁移**：`CLAUDE.md` §1.8 写"迁移文件不上传、本地生成服务器手动执行"，但 `CLAUDE.md` §7 与 `.github/copilot-instructions.md` §8 又要求"commit 必须含迁移文件"。**可执行真相：Git 实际追踪 134 个迁移文件，最新一条提交于 2026-06-16**（未被 `.gitignore` 排除）。→ **现行做法是随 Model 变更一起提交迁移文件**；`CLAUDE.md` §1.8 已过时，修改 Model 时请按 §7 执行，并建议择机清理 §1.8。
- `CLAUDE.md` §6.8 描述的 3 个 Celery worker systemd service（`celery-default` / `celery-parallel` / `celery-single`，并发 4/8/1）属运维端部署形态，**仓库内无法验证**，仅供参考；以实际服务器 `-Q` 配置为准。
