# 新增功能标准流程

本文给出在本系统中新增一个业务功能的标准步骤，确保不遗漏架构约定与知识库同步。

## 一、后端新增功能

以「新增一个 XX 业务模块」为例：

1. **Model**：在 `api_v1/models/<板块>/` 新建 `xxx.py`，一个 Model 一个文件，遵循 Model 优雅书写铁律（顶部 docstring 含表名、字段多行展开、`verbose_name` 关键字参数、`Meta` 三件套、`__str__`）。
2. **Serializer**：在 `api_v1/serializers/<板块>/` 新建 `xxx_serializer.py`。
3. **Service**：在 `api_v1/services/<板块>/` 新建 `xxx_service.py`，承载业务计算与外部调用。
4. **View**：在 `api_v1/views/<板块>/` 新建 `xxx_view.py`，仅做 HTTP 解析与出参包装。
5. **URL**：在 `api_v1/urls.py`（或板块 `urls/` 包）注册路由。
6. **板块 `__init__.py`**：子目录 `__init__.py` 显式 `from .xxx import XxxClass` 重导出。
7. **迁移**：本地 `python manage.py makemigrations` 验证可生成；commit 只含 Model 文件，不含迁移文件；给出服务器端迁移命令。

## 二、前端新增功能

1. **API 模块**：在 `src/api/<板块>/` 新建 `xxx.ts`，封装请求，禁在视图直接 `axios`。
2. **类型定义**：在 `src/types/<板块>/` 新建 `xxx.ts`。
3. **Composable**：在 `src/composables/<板块>/` 新建 `useXxx.ts`（如有逻辑复用）。
4. **页面视图**：在 `src/views/<板块>/` 新建 `XxxPage.vue`（`PascalCase`），三段式，≤ 400 行，顶部中文 JSDoc。
5. **路由**：在 `src/router/` 注册（或由后端菜单动态下发）。
6. **绝对路径导入**：全程 `@/...`。

## 三、新增 Celery 任务

按 Celery 任务标准 5 步（见 `05-celery-tasks.md`）：写任务文件 → `tasks/__init__.py` 注册 → `CELERY_TASK_ROUTES` 加路由 → 重启 Django → 重启 worker。如需加锁，按三层防御方案。

## 四、提交前验证

- 前端：`pnpm run type-check` + `pnpm run lint:eslint`。
- 后端：`python manage.py runserver` 手动联调（无自动化测试套件）。
- 确认无未使用变量、lint 警告、`any` / `@ts-ignore` 残留。

## 五、同步知识库（铁律）

新增或变更任何对外功能后，**必须同步更新 `docs/knowledge-base/` 对应文档**：

- 新增业务模块 → 在 `user-guide/` 新增使用说明，并在 `README.md` 目录结构登记。
- 新增 Celery 任务 / 接口 / 模型 → 更新 `developer-guide/` 对应章节。
- 新增环境变量 / 管理命令 / 部署变更 → 更新 `ops-guide/` 对应章节。
- 变更已有功能行为 → 修改对应文档，删除过时描述。
- 文档修改后，在 Dify 知识库中重新上传对应文件。

此规则已写入 `CLAUDE.md` 与 `AGENTS.md` 铁律，未同步知识库视为任务未完成。
