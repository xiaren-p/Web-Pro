# AGENTS.md

本文件与 `CLAUDE.md` 内容同步，是项目工程规范总纲（已纳入 Git，会话自动加载）。
`.opencode/skills/` 下 Skill 为**唯一事实源**，AI 按任务类型精确加载。

> 路由清单：`.opencode/MANIFEST.md`（任务意图 → Skill 路径映射）

## Skill 加载指令（每次会话必读）

**前端任务执行前，必须按意图加载对应 Skill：**

| 维度 | 任务 | 加载 |
|------|------|------|
| 🏗️ 架构 | CURD/API/权限/布局/Store/路由/代码约束 | `project-conventions` | 🔴 最高 |
| 🏗️ 架构 | 写 Vue 组件/Composable | `vue-best-practices` + `vue-antfu` |
| 🏗️ 架构 | 写 Store | `vue-pinia-best-practices` |
| 🏗️ 架构 | 写路由/守卫 | `vue-router-best-practices` |
| 🏗️ 架构 | 写 Composable 合约 | `create-adaptable-composable` |
| 🔒 安全 | 用户输入/认证/v-html/依赖 | `security-hardening` |
| 🔒 安全 | 安全审计/漏洞扫描 | `security-audit` |
| ⚡ 性能 | 页面加载/Web Vitals | `core-web-vitals` |
| ⚡ 性能 | 全栈性能审计 | `performance-audit` |
| ✅ 质量 | 代码审查 | `code-review` |
| 📝 注释 | 写 JSDoc/函数级注释 | `inline-documentation` |
| 📝 技术文档 | 功能实现后写技术文档/变更说明 | `technical-writing` | 🔴 每次更新代码必须 |
| 🎨 设计 | UI 设计质量 | `frontend-design` |

**后端任务执行前，必须按意图加载对应 Skill：**

| 维度 | 任务 | 加载 |
|------|------|------|
| 🏗️ 架构 | Model/Service/Selector/View 分层 | `backend-django-arch` | 🔴 最高 |
| 🏗️ 架构 | 脚手架/工具链/CI | `backend-django-project` | ◎ 参考 |
| 🔒 安全 | 安全审计/漏洞扫描 | `security-audit` | 前后端共享 |
| ⚡ 性能 | 全栈性能/慢查询/N+1 | `performance-audit` | 前后端共享 |
| ✅ 质量 | Python 审查 (PEP8/mypy/pytest) | `code-review`（`reference/python.md` 524行） |
| ✅ 质量 | Django 审查 (N+1/CBV/ORM) | `code-review`（`reference/django.md` 966行） |
| 📝 注释 | 写 Python Docstring | `inline-documentation` | 前后端共享 |
| 📝 技术文档 | 功能实现后写技术文档/变更说明 | `technical-writing` | 🔴 每次必须 |

> Skill 路径格式：`.opencode/skills/<skill-name>/SKILL.md`
> **后端项目专属可执行真理见本文件 §后端 Django 规范**（Celery 路由/加锁/迁移闭环/日志等）

---

## 规范体系与优先级

- **前端 Skill 优先级**：① `project-conventions`（CURD/API/权限/布局/Store/路由/代码约束）—— 最高 ② 架构层（vue-best-practices/pinia/router/composable）③ 安全层（hardening/audit）④ 性能层（core-web-vitals/performance-audit）⑤ 质量层（code-review/frontend-design/inline-documentation）
- **后端 Skill 优先级**：① `backend-django-arch`（Model/Service/Selector/View 分层 + 异常 + 性能）② 共享层（code-review/security-audit/performance-audit/inline-documentation）
- **执行时以"可执行真相"为准**：当文档与配置/脚本/Git 实际冲突时，信任可执行源。

## 全局通用原则

- **阅后即焚**：临时脚本/文件排查完必须删除，禁止推入主库。
- **技术文档闭环**：每次功能实现或重大重构完成后，必须输出一份技术文档（feature doc / 变更说明）。详见 Skill `technical-writing`。

## AI 编码行为铁律（最高优先级）

- 不确定就停下来问；YAGNI；只碰必须碰的；修 bug 先写复现测试。
- 数学/格式化/日期/类型转换用普通代码，不拿 AI 推理。
- 发邮件/短信、改生产 DB、删文件/分支、强推、调付费 API——必须先请示。
- 先读懂再写：读 exports、caller、utility、命名惯例；禁止只看文件名/签名就开写。
- 反复修同一个 bug 修不好时 → 开新对话 → 先评估再修复。

## 后端 Django 规范（`backend-master/`）

> **后端架构 Skill**：`.opencode/skills/backend-django-arch/SKILL.md` — Model/Service/Selector/View 分层 + 异常体系 + 性能模式 + 检查清单。
> **质量 Skill**：`.opencode/skills/code-review/SKILL.md` — 内含 `reference/django.md`（966行）和 `reference/python.md`（524行）。
> **专业重构方向**：新代码按 Skill 的 Service/Selector 分层写，旧代码不动。项目 `api_v1/` 目录结构不变，分层思想按实际子目录适配。
> **适配说明**：Skill 使用 `apps/{name}/` 扁平结构，本项目使用 `api_v1/` 子目录结构。分层思想通用，目录路径按项目实际调整。
> **Celery 专属规则**：下方 Celery 路由/加锁/5步注册/三队列 为本项目专属可执行真理，Skill 不覆盖，但与 Skill 的通用 Celery 模式互补。

### 命令与环境

- 所有命令在 `backend-master/` 下执行，`DJANGO_SETTINGS_MODULE=backend_master.settings`。
- **`backend-master/.env` 被 gitignore 且必需**：DB / `FERNET_SECRET_KEY` / `REDIS_URL` / `DIFY_API_KEY` / OIDC 私钥等均依赖此文件。
- 开发服务器：`python manage.py runserver`。
- **后端无自动化测试套件**：不要假设存在 `pytest` / `tox` / `ruff` 命令。验证靠 `runserver` 手动联调 + 前端 `vue-tsc` / `eslint`。
- 自定义管理命令：`sync_system_menus`、`setup_nc_oidc_client`、`generate_oidc_key`、`purge_file_module_artifacts`、`audit_orphans`、`reconcile_nc` 等。

### Celery 部署与路由

- **Worker 启动必须显式列出所有队列**：`celery -A backend_master worker -l info -Q celery,parallel_queue,single_thread_queue`
- Beat：`celery -A backend_master beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`
- **路由唯一声明位置**：`settings.CELERY_TASK_ROUTES`。禁止在 `@shared_task` 写 `queue=`，禁止 `apply_async(queue=...)` 绕过路由表。
- **三队列**：<30s → `celery`；≥30s 可并发 → `parallel_queue`（concurrency=4）；≥30s 串行 → `single_thread_queue`（concurrency=1）。

### 新增 Celery 任务 5 步（漏一步即"任务静默不执行"）

1. 写任务文件，`@shared_task` 的 `name=` 必须 = 完整模块路径，禁止省略、禁止写 `queue=`
2. `tasks/__init__.py` 显式 import 并加入 `__all__`
3. `settings.CELERY_TASK_ROUTES` 追加一行
4. 重启 Django Web
5. 重启目标队列的 Celery worker

### Celery 任务加锁

- 统一用 `api_v2/utils/task_execution_lock.py`
- 三层防御：① `single_thread_queue` concurrency=1 ② `TaskExecutionLock` ③ `is_task_running` 提前 409
- 硬规则：视图禁 `cache.add` 写锁；`LOCK_TTL ≥ time_limit + 60`；`acks_late=True`；409 用 `BUSY_RESPONSE`

### Model 优雅书写

- `meta 三件套：verbose_name / verbose_name_plural / ordering`
- `choices` 走 `TextChoices` / `IntegerChoices`
- `def __str__(self) -> str:` 返回有辨识度字段
- `managed=False` 显式标注 + `db_table`

### 响应格式

统一使用 `drf_ok()` / `drf_error()`，响应结构为 `{code, data, msg}`：

| Code | 含义 | 触发场景 |
|------|------|---------|
| `00000` | 成功 | 所有正常响应 |
| `B0001` | 业务错误 / 任务冲突 | 参数校验失败、业务规则不满足、`BUSY_RESPONSE` 任务执行中 (409) |
| `A0201` | 未登录 | Token 无效/过期/缺失 |
| `A0301` | 无权限 | 权限不足 |
| `A0404` | 资源不存在 | 记录未找到 |
| `B0500` | 服务器错误 | 未捕获异常、未知错误 |

### 数据库

- 双数据库：`default`（MySQL）+ `analytics`（Doris）

---

## 前端 Vue3 规范（`vue3-element-admin-master/`）

> **所有前端编码规则见对应的 Skill 文件**（`.opencode/skills/`）。下方仅保留 Skill 无法替代的"可执行真相"。

### 命令与陷阱

- **包管理器强制 pnpm**：`preinstall` 跑 `npx only-allow pnpm`，Node `^20.19.0 || >=22.12.0`
- `pnpm run dev` — 开发服务器（端口 `VITE_APP_PORT` = 3000）
- `pnpm run type-check` — `vue-tsc --noEmit`（**不是** `typecheck`）
- `pnpm run lint` — 串联 `lint:eslint` + `lint:prettier` + `lint:stylelint`
- 提交前至少跑 `pnpm run type-check` + `pnpm run lint:eslint`
- 提交钩子强制 Conventional Commits：`feat|fix|docs|style|refactor|perf|test|build|ci|revert|chore|wip`

## Markdown 文档规范

- 中英混排空格；ATX 标题全文仅一个 `# H1`，禁跳级
- 代码块标语言；禁敏感硬编码（API Key 等用 `<YOUR_xxx>` 替换）

## Git 提交规范

- 提交前确保 lint + type-check 通过
- 禁将临时文件推进主库
- **`.opencode/` 不上传 Git**（已在 `.gitignore` 排除）
