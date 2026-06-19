# AGENTS.md

本文件是 `CLAUDE.md`（项目工程规范总纲，已纳入 Git，会话自动加载）的高密度执行备忘。按 `CLAUDE.md` 八大节顺序搬运核心规则并标注章节号，便于一眼定位 + 跳转查全文；同时补充经仓库验证的"可执行真相"（命令、陷阱、文档冲突）。通用编程常识不在此重复。

## 规范体系与优先级（CLAUDE.md §8）

- **权威总纲**：`CLAUDE.md`（根，已追踪）是唯一随仓库分发的规范，会话自动加载。所有详细架构与语言细则都在其中。
- **语言专属细则**：`.github/copilot-instructions.md` 与 `.github/instructions/{python,frontend,markdown,architecture}.instructions.md` 是细化强约束，**但 `.github/` 整体被 `.gitignore` 排除（0 个文件被追踪）**。全新 clone 的环境拿不到这些细则，只有 `CLAUDE.md`。需要细则时优先读 `CLAUDE.md`，缺失部分再参考本地 `.github/instructions/`。
- **冲突优先级**（CLAUDE.md §8）：① AI 编码行为铁律（§2）—— 最高 ② 文件所在目录的专用章节（后端 → §3、§5.1；前端 → §4、§5.2）③ 全局通用原则（§1）④ 测试文件（§5.3）。
- **执行时以"可执行真相"为准**：当文档与配置/脚本/Git 实际冲突时，信任可执行源（见文末"已知文档冲突"）。

## 全局通用原则（CLAUDE.md §1）

- **英文命名 + 中文注释**（§1.1）：类/变量/函数/数据库字段全英文，禁拼音、禁中英混搭；类与函数必须强制完整中文 Docstring，讲清"为什么（Why）"。技术债标记 `# TODO(优化/张三): 待XX优化` / `// FIXME(Bug/李四): ...`。
- **反屎山**（§1.2）：物理文件拆分、卫语句前置拦截（嵌套 ≤ 3 级）、函数 ≤ 50 行、禁硬编码（提常量/枚举/环境变量）。
- **日志基线**（§1.3）：生产代码禁 `print()` / `console.log()`，走 Logger；后端每条日志带 `[类名] [方法名]` 前缀，`ERROR` 带 `exc_info=True`；禁裸 `except: pass`。
- **分层 + 非阻塞**（§1.4）：UI/Controller 与 Service 物理分离；耗时 IO/计算入异步任务/线程池/协程。
- **阅后即焚**（§1.5）：临时脚本、Mock JSON、`test_xxx`（非官方测试）、`temp_run.py` 排查完必须删除，禁止推进主库。
- **依赖同步**（§1.6）：新增第三方包必须同步写入 `requirements.txt` / `package.json`。
- **命名美学**（§1.7）：禁 `do_stuff.py` / `temp_run.js` 等脚本味命名；Python `snake_case.py`、前端组件 `PascalCase.vue`、文档 `kebab-case.md`。
- **数据库迁移闭环**（§1.8）：迁移文件**不上传**——本地 `makemigrations` 生成的 `xxxx_*.py` 仅用于开发验证，生产由运维在服务器手动执行；commit 只含 Model 文件，不含迁移文件。AI 改动 Model 后必须给出服务器端 `makemigrations` + `migrate` 步骤（遇冲突给 `--fake` 或手动 SQL），禁止替服务器执行。
- **Dify 知识库同步闭环**（§1.9）：`docs/knowledge-base/` 是喂给 Dify 聊天机器人的知识库（按 user/developer/ops 三类受众组织，索引见其 `README.md`）。**新增或变更对外功能必须同步更新对应章节**——新业务模块→`user-guide/`、新任务/接口/模型→`developer-guide/`、新环境变量/命令/部署→`ops-guide/`；未同步视为任务未完成。文档遵循 §6 Markdown 规范，命名 `kebab-case.md`；Dify 侧重新上传由用户手动完成。

## AI 编码行为铁律（CLAUDE.md §2，最高优先级）

- **先思考再编码**（铁律 1）：不确定就停下来问，列选项让用户选，不瞎猜、不隐藏困惑。
- **简洁优先**（铁律 2）：YAGNI，不加未被要求的功能/抽象/灵活性；200 行能写成 50 行就重写；不创建 < 3 个实现的抽象类。
- **精准修改**（铁律 3）：只碰必须碰的，匹配现有风格，不顺手优化相邻代码；发现死代码**提一句别动手删**，让用户决定。
- **目标驱动**（铁律 4）：修 bug 先写复现测试；多步任务列每步验证标准；未经验证不说"完成"。
- **确定性优先**（进阶 5）：数学/格式化/日期/类型转换用普通代码，不拿 AI 推理。
- **人在回路**（进阶 7）：发邮件/短信、改生产 DB、删文件/分支、强推、调付费 API、发布生产——必须先请示。
- **先读懂再写**（进阶 9）：读目标文件 exports、caller、共用 utility、相邻文件命名惯例；禁止只看文件名/签名就开写。
- **失败要大声揭露**（进阶 12）：不确定主动标记，影响范围主动列出，风险主动声明；宁多报 3 个假警报不漏 1 个真问题。
- **死亡循环**：反复修同一个 bug 修不好时，停止 → 开新对话 → 先评估报告再修复。

## 后端 Django 规范（CLAUDE.md §3、§5.1，`backend-master/`）

### 命令与环境

- 所有命令在 `backend-master/` 下执行，`DJANGO_SETTINGS_MODULE=backend_master.settings`。
- **`backend-master/.env` 被 gitignore 且必需**：`django-environ` 读取它，DB / `FERNET_SECRET_KEY` / `REDIS_URL` / `DIFY_API_KEY` / OIDC 私钥等均依赖此文件，没有 `.env` 服务起不来。
- 开发服务器：`python manage.py runserver`。
- **后端无自动化测试套件**：`requirements.txt` 含 `pytest`，但仓库内无 `tests/`、无 `pytest.ini` / `pyproject.toml` 配置。验证靠 `runserver` 手动联调 + 前端 `vue-tsc` / `eslint`。不要假设存在 `pytest` / `tox` / `ruff` 命令。
- 自定义管理命令（`api_v1/management/commands/`）：`sync_system_menus`、`setup_nc_oidc_client`、`generate_oidc_key`、`purge_file_module_artifacts`、`audit_orphans`、`reconcile_nc` 等，部署/运维常用。

### Celery 部署与路由（CLAUDE.md §6）

- **Worker 启动必须显式列出所有队列**，否则未列出的队列任务永远不执行：
  ```bash
  celery -A backend_master worker -l info -Q celery,parallel_queue,single_thread_queue
  ```
- Beat：`celery -A backend_master beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`。
- **路由唯一声明位置**：`backend_master/settings.py` 的 `CELERY_TASK_ROUTES`（CLAUDE.md §6.3）。**禁止**在 `@shared_task` 写 `queue=`，**禁止**调用方 `apply_async(queue=...)` 绕过路由表。
- **三队列决策树**（§6.4）：耗时 < 30s 轻量 → `celery`；≥ 30s 且可并发 → `parallel_queue`（concurrency=4）；≥ 30s 且须串行/写同资源/调有 QPS 限制的外部 API → `single_thread_queue`（concurrency=1）。

### 新增 Celery 任务标准 5 步（CLAUDE.md §6.5，漏一步即"任务静默不执行"）

1. 写任务文件 `api_v2/tasks/xxx_task.py`（或 `api_v1/tasks/`），`@shared_task` 的 `name=` 必须 = 完整模块路径（如 `api_v2.tasks.xxx_task.run_xxx_task`），**禁止**省略 `name=` 让 Celery 自动生成，**禁止**写 `queue=`。
2. 在 `api_v2/tasks/__init__.py`（或 `api_v1/tasks/__init__.py`）**显式 `import` 该任务并加入 `__all__`**——不注册则 worker 启动时不加载，派发会报 `Received unregistered task` 然后被丢弃。
3. 在 `settings.CELERY_TASK_ROUTES` 追加一行，key 与装饰器 `name` 一字不差，按决策树选队列，保留三段注释分组。
4. **重启 Django Web**（路由表是 Django 派发时读的）。
5. **重启目标队列的 Celery worker**（worker 启动时才扫描 `tasks/__init__.py`）。

### Celery 任务加锁（CLAUDE.md §5，唯一合法方案）

- 统一用 `api_v2/utils/task_execution_lock.py`：`is_task_running(lock_key)`（视图只读检查）、`TaskExecutionLock(lock_key, ttl)`（任务体上下文管理器）、`BUSY_RESPONSE(msg)`（标准 409，错误码 `B0001`）。
- **三层防御必须全到位**（§5.2）：① 队列层 `single_thread_queue` concurrency=1 ② 任务体 `with TaskExecutionLock(...)` ③ 视图层 `is_task_running` 提前 409。
- **硬规则**（§5.6）：视图禁止 `cache.add` 写锁（只能 `is_task_running` 读）；`LOCK_KEY` 必须由任务模块导出、视图 `from import` 复用；`LOCK_TTL ≥ time_limit + 60`；`acks_late=True` 必须开；抢锁失败必须返回 schema 完整 dict（如 `{"processed": 0, "errors": [...]}`）；409 必须用 `BUSY_RESPONSE`。
- **纯 Beat 高频任务（无 HTTP 视图）**（§5.9）：schedule ≤ 60s 必须加 `options.expires` 且 `expires < schedule`（防止 Beat 堆积），参考 `listing_tag_sync`（schedule=5, expires=4）。
- 任务/视图标准模板见 CLAUDE.md §5.3 / §5.4。

### 代码规范（CLAUDE.md §3）

- **绝对路径导入**：`from api_v1...` / `from api_v2...`，**禁相对导入**。
- **Google Style 中文 Docstring**：类/函数强制完整 Docstring，含 `Args` / `Returns` / `Raises` / `Examples`。
- **强制 Type Hints**：入参/返回值/类属性必须标注，禁 `Any` 铺满（兜底需注释原因）。
- **卫语句 + 嵌套 ≤ 3**；方法 > 50 行抽 `_xxx`；禁 `# ======` 长分隔注释，改 `# 主题：说明`。
- **网络/文件鲁棒性**：`requests` 必须写 `timeout`；`with open` 释放句柄；批量遍历切片，禁多层 `for` 嵌套；禁 `try...except Exception: pass`。

### 后端架构（CLAUDE.md §5.1）

- **一类一文件**（§5.1.x）：每个 Model / Serializer / View / Middleware / Permission / Auth / Service / Celery Task 一个 `.py`，禁 `models.py` / `serializers.py` 等巨型聚合文件。
- **板块化分组**：同板块用同名子目录聚合（`api_v1/models/ads/`、`api_v1/views/ads/`），子目录 `__init__.py` 显式 `from .xxx import XxxClass` 重导出；跨板块基础类放 `common/`。
- **职责归类**：字段映射/校验 → `serializers/`；表结构/关联/Manager → `models/`；业务计算/跨模型聚合/外部调用 → `services/`；HTTP 解析/出参包装 → `views/`。禁 view 拼字典、禁 model 写跨表计算。
- **`api_v2`** 是与 `api_v1` 对称的独立 App，专职工作流任务调度与异步执行，不承载 CRUD；鉴权与 `api_v1` 共享，可直接导入其 models/services。

### Model 优雅书写（CLAUDE.md §5.1.y）

- 模块顶部 docstring 含表名（`managed=False` 须注明）；类中文 docstring；字段多行展开、字段间空行；`verbose_name` 强制关键字参数；`choices` 走 `TextChoices` / `IntegerChoices`；`Meta` 三件套（`verbose_name` / `verbose_name_plural` / `ordering`）齐全，`managed=False` 须显式 `managed = False` + `db_table`；`def __str__(self) -> str:` 返回有辨识度字段。标准范式见 §5.1.y。

### 鉴权与响应（可执行真相）

- DRF 仅 `api_v1.auth.BearerTokenAuthentication`，Session 认证已从 DRF 移除（OIDC SSO 走 Django 模板视图，不经过 DRF）。外部应用走 OAuth2 Client Credentials（`/o/token/`，scope `api_v2`）。
- 统一响应 `{code, data, msg}`，成功 `code="00000"`；分页 `{total, list}`。异常经 `api_v1.utils.responses.custom_exception_handler` 统一处理。
- **双数据库**：`default`（MySQL，业务）+ `analytics`（Doris，分析），由 `backend_master/analytics_database_router.AnalyticsDatabaseRouter` 路由。

## 前端 Vue3 规范（CLAUDE.md §4、§5.2，`vue3-element-admin-master/`）

### 命令与陷阱

- **包管理器强制 pnpm**：`package.json` 的 `preinstall` 跑 `npx only-allow pnpm`，用 `npm` / `yarn` 安装直接失败。Node 要求 `^20.19.0 || >=22.12.0`。
- 关键脚本（`pnpm run <name>` 或 `npm run <name>` 均可，安装必须 pnpm）：
  - `dev` — Vite 开发服务器，端口取自 `VITE_APP_PORT`（`.env.development` = 3000，未设回退 5173）。
  - `type-check` — **是** `vue-tsc --noEmit`（**不是** `typecheck`）。
  - `lint` — 串联 `lint:eslint` + `lint:prettier` + `lint:stylelint`。
  - `build` — `vue-tsc --noEmit & vite build`。
- **提交钩子**：`pre-commit` 跑 `lint:lint-staged`（只校验暂存文件）；`commit-msg` 跑 `commitlint`，强制 Conventional Commits 且 **type 枚举自定义**：`feat|fix|docs|style|refactor|perf|test|build|ci|revert|chore|wip`。交互式提交用 `npm run commit`（commitizen）。
- 改动前端代码后，提交前至少跑 `pnpm run type-check` 与 `pnpm run lint:eslint`。

### API / 代理约定

- 开发态请求统一走 `/dev-api` 前缀（`VITE_APP_BASE_API=/dev-api`），由 `vite.config.ts` 的 proxy 重写后转发到 `VITE_APP_API_URL`（默认 `http://127.0.0.1:8000/api/v1`）。
- proxy 规则（`vite.config.ts`）：`/dev-api/media/*` → `/media/*`；`/dev-api/(api/v[2-9]|o)/` 仅剥前缀保留路径；其余 → `/api/v1`。
- 后端对应入口：`/api/v1/`、`/api/v2/`、OAuth2 `/o/`，另有 `/prod-api/` 兼容别名（见 `backend_master/urls.py`）。
- **所有网络请求必须经 `src/api/<板块>/` 封装**，禁在视图/组件直接 `axios` / `fetch`（CLAUDE.md §4.3、§5.2）。

### 代码规范（CLAUDE.md §4）

- **绝对路径导入**：`@/...` 别名，**禁相对路径**（`../../api/xxx`）。
- **强制 `<script setup lang="ts">`**：禁 Options API（`data()` / `methods` / `mixins`），禁裸 `<script>`。
- **JSDoc 中文注释**：类/对外函数必须 `/** ... */` 块 + `@param` / `@returns` / `@throws`。
- **消灭 `any`**：动态参数走 `unknown` + 类型守卫；禁 `@ts-ignore` / `eslint-disable` 静默错误（特殊情况须跟中文 TODO）。
- **样式隔离**：`<style scoped lang="scss">`，穿透只用 `:deep()` 且在父级选择器内。
- **网络熔断**：触发后端通信的按钮先 `loading.value = true`；`401/403/500` 收拢于 Axios Response Interceptors。

### 前端架构（CLAUDE.md §5.2）

- **一文件一职责**（§5.2.x）：每个 SFC / Store / Composable / API 模块一个文件。命名：View/Component `PascalCase.vue`、Composable `useXxx.ts`、Store `xxxStore.ts`、API `xxx.ts`。
- **板块化分组**：同板块同名子目录聚合（`src/views/listing/`、`src/api/listing/`）；`index.ts` 显式 `export { useXxx } from './useXxx'`，**禁**桶文件 `export *`。
- **数据出口最终成形**（§5.2 通用治理）：枚举翻译/金额/日期/单位格式化/字段重命名/聚合统计必须在**后端**完成；前端拿到即可渲染，**禁**在 `views` / `components` / `composables` 做业务字段重映射或格式化。

### SFC 优雅书写（CLAUDE.md §5.2.y）

- **三段式顺序固定**：`<template>` → `<script setup lang="ts">` → `<style scoped lang="scss">`。
- **`<script>` 内部分区顺序**：类型导入 → 第三方库 → `@/` 项目内 → `defineProps` / `defineEmits` / `defineExpose` → 响应式状态 → Composable/Store → 业务函数 → 生命周期。
- **`defineProps` 带 TS 泛型**、**`defineEmits` 显式签名**；模板自定义标签 `kebab-case`，属性顺序 `指令 → ref/key → props → 事件`。
- **单 SFC ≤ 400 行**（含模板与样式），超出拆子组件 / Composable；顶部须有中文 JSDoc 业务注释。标准范式见 §5.2.y。

## Markdown 文档规范（CLAUDE.md §6）

- **中英混排空格**：中文与英文单词、数字、`` `xxx` `` 之间必须手动插半角空格。
- **ATX 标题**：全文仅一个 `# H1`，禁跳级，标题末尾禁冒号。
- **代码块标语言**：```` ```python ```` / ```` ```bash ```` / ```` ```yaml ```` 等。
- **禁敏感硬编码**：API Key / 生产 DB 账号 / 真实 IP 用 `<YOUR_xxx>` 替换。
- 复杂流程用 Mermaid.js（`flowchart` / `sequenceDiagram`）。

## Git 提交规范（CLAUDE.md §7）

- 提交前确保无未使用变量、未处理警告、违反 `eslint.config.ts` 的语法问题。
- 禁 `// eslint-disable-next-line` / `@ts-ignore` 掩盖错误（特殊情况跟中文 TODO）。
- **变更 Model 时 commit 只含 Model 文件**，不含迁移文件（CLAUDE.md §1.8）；AI 需同步给出服务器端 `makemigrations` + `migrate` 迁移命令。
- 禁将 `test_xxx`（非官方测试）/ `temp_run.py` 等临时文件推进主库。

## 已知文档冲突（以可执行真相为准）

- **数据库迁移**：规则以 `CLAUDE.md` §1.8 为准——迁移文件不上传、commit 只含 Model 文件、本地生成服务器手动执行；`CLAUDE.md` §7 已同步对齐 §1.8（原"commit 必须含迁移文件"已修正）。⚠️ Git 当前仍追踪 **134 个历史迁移文件**（截至 2026-06-16），未被 `.gitignore` 排除，属历史遗留，与"不上传"规则不符；经确认**保持现状，仅约束未来**——后续 Model 变更勿再提交迁移文件。
- `CLAUDE.md` §6.8 描述的 3 个 Celery worker systemd service（`celery-default` / `celery-parallel` / `celery-single`，并发 4/8/1）属运维端部署形态，**仓库内无法验证**，仅供参考；以实际服务器 `-Q` 配置为准。
