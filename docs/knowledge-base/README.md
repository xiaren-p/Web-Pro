# ERP 系统知识库

本目录是喂给 **Dify 聊天机器人** 的知识库文档集合。聊天机器人基于这些文档回答三类人群的问题：

- **最终用户**：怎么使用系统的某个功能（操作步骤、字段含义）
- **开发者**：系统的架构、接口、Celery 任务、开发规范
- **运维**：环境变量、部署启动、数据库迁移、管理命令、排障

## 目录结构

```text
docs/knowledge-base/
├── README.md                      本文件（索引 + 导入说明 + 维护流程）
├── 00-system-overview.md          系统总览（业务定位、技术栈、架构）
├── user-guide/                    面向最终用户的使用说明
├── developer-guide/               面向开发者的架构与接口
└── ops-guide/                     面向运维的部署与命令
```

## 如何导入 Dify 知识库

1. 进入 Dify 平台 → 知识库 → 创建知识库。
2. 上传方式选「文本文件」，把 `docs/knowledge-base/` 下所有 `.md` 文件拖入。
3. 分段策略建议：
   - 分段方式：**自动分段** 或 **按段落（`\n\n`）**。
   - 最大分段长度：建议 500~800 token，避免单段过长导致检索精度下降。
   - 重叠长度：50~100 token，保留上下文。
4. 索引方式：**高质量**（若平台资源允许）或经济模式。
5. 检索测试：导入后在「召回测试」里输入「怎么给 Listing 打标签」「Celery worker 怎么启动」「AI 助手怎么用 Plan」等，确认能命中对应段落。
6. 在 AI 助手应用中关联该知识库，并调整提示词：要求优先依据知识库回答，知识库未覆盖时再由模型作答。

> 文档命名遵循 `kebab-case.md`，与项目 `CLAUDE.md` 文档规范一致。

## 维护铁律（新功能必须同步知识库）

项目 `CLAUDE.md` 与 `AGENTS.md` 已写入铁律：**新增或变更任何对外功能时，必须同步更新本知识库对应章节**。具体规则见 `CLAUDE.md` 第一章第 9 条与 `AGENTS.md`「知识库维护」一节。

维护要点：

- 新增业务模块 → 在 `user-guide/` 新增一篇使用说明，并在本 README 目录结构中登记。
- 新增 Celery 任务 / 接口 / 模型 → 更新 `developer-guide/` 对应章节。
- 新增环境变量 / 管理命令 / 部署变更 → 更新 `ops-guide/` 对应章节。
- 变更已有功能行为 → 同步修改对应文档，删除过时描述。
- 文档修改后，需在 Dify 知识库中重新上传对应文件（Dify 支持单文件覆盖更新）。

## 文档清单

### 总览

- `00-system-overview.md` — 系统总览

### 用户指南（`user-guide/`）

- `01-dashboard.md` — 首页仪表盘
- `02-sales-listing.md` — 商品 Listing 管理
- `03-sales-listing-tag.md` — Listing 标签管理
- `04-sales-image-upload.md` — 商品图片上传
- `05-ads-sp.md` — SP 广告管理
- `06-ads-tools-strategy.md` — 广告工具（规则策略 / 分时调价）
- `07-ai-assistant.md` — AI 助手
- `08-statistics-loss.md` — 亏损订单统计
- `09-system-user.md` — 用户管理
- `10-system-dept.md` — 部门管理
- `11-system-position.md` — 岗位管理
- `12-system-menu.md` — 菜单管理
- `13-system-dict.md` — 字典管理
- `14-system-config.md` — 参数配置
- `15-system-notice.md` — 通知公告
- `16-system-log.md` — 操作与访问日志
- `17-system-nc.md` — Nextcloud 文件夹树
- `18-developer-apps.md` — 开发者应用管理
- `19-work-report.md` — 工作汇报
- `20-crawler.md` — 数据采集
- `21-profile.md` — 个人中心

### 开发者指南（`developer-guide/`）

- `01-architecture.md` — 整体架构与技术栈
- `02-directory-layout.md` — 目录结构
- `03-api-v1.md` — api_v1 接口总览
- `04-api-v2.md` — api_v2 接口总览
- `05-celery-tasks.md` — Celery 任务体系
- `06-auth-response.md` — 鉴权与统一响应
- `07-database.md` — 数据库（双库）
- `08-ai-assistant-stack.md` — AI 助手技术栈
- `09-conventions.md` — 开发规范要点
- `10-new-feature.md` — 新增功能标准流程

### 运维指南（`ops-guide/`）

- `01-environment.md` — 环境变量
- `02-deploy.md` — 部署与启动
- `03-celery.md` — Celery worker 与 beat
- `04-migrations.md` — 数据库迁移
- `05-management-commands.md` — 管理命令
- `06-oidc-nc.md` — OIDC 与 Nextcloud 配置
- `07-troubleshooting.md` — 常见问题排查

## Dify 知识库元数据方案

知识库采用**单知识库 + 元数据过滤**架构（服务一个聊天机器人，检索时按元数据精准过滤）。在 Dify 知识库界面右上角「元数据」中创建以下 3 个自定义字段：

| 字段名 | 值类型 | 取值 | 作用 |
| --- | --- | --- | --- |
| `audience` | 字符串 | `user` / `developer` / `ops` | 按提问者身份过滤 |
| `module` | 字符串 | 见下表 | 按业务模块过滤 |
| `doc_type` | 字符串 | `guide` 操作指南 / `reference` 接口字段参考 / `troubleshooting` 排障 | 按问题类型过滤 |

### 每篇文档的元数据标签映射

上传文档后，按下表逐篇（或按目录批量）编辑元数据：

| 文档 | audience | module | doc_type |
| --- | --- | --- | --- |
| `00-system-overview.md` | user | overview | guide |
| `README.md` | developer | overview | guide |
| **user-guide/** | | | |
| `01-dashboard.md` | user | dashboard | guide |
| `02-sales-listing.md` | user | listing | guide |
| `03-sales-listing-tag.md` | user | listing | guide |
| `04-sales-image-upload.md` | user | listing | guide |
| `05-ads-sp.md` | user | ads | guide |
| `06-ads-tools-strategy.md` | user | ads | guide |
| `07-ai-assistant.md` | user | ai_assistant | guide |
| `08-statistics-loss.md` | user | statistics | guide |
| `09-system-user.md` | user | system | guide |
| `10-system-dept.md` | user | system | guide |
| `11-system-position.md` | user | system | guide |
| `12-system-menu.md` | user | system | guide |
| `13-system-dict.md` | user | system | guide |
| `14-system-config.md` | user | system | guide |
| `15-system-notice.md` | user | system | guide |
| `16-system-log.md` | user | system | guide |
| `17-system-nc.md` | user | nc | guide |
| `18-developer-apps.md` | user | system | guide |
| `19-work-report.md` | user | work_report | guide |
| `20-crawler.md` | user | crawler | guide |
| `21-profile.md` | user | system | guide |
| **developer-guide/** | | | |
| `01-architecture.md` | developer | overview | guide |
| `02-directory-layout.md` | developer | overview | reference |
| `03-api-v1.md` | developer | api | reference |
| `04-api-v2.md` | developer | api | reference |
| `05-celery-tasks.md` | developer | celery | reference |
| `06-auth-response.md` | developer | auth | reference |
| `07-database.md` | developer | database | reference |
| `08-ai-assistant-stack.md` | developer | ai_assistant | reference |
| `09-conventions.md` | developer | overview | guide |
| `10-new-feature.md` | developer | overview | guide |
| **ops-guide/** | | | |
| `01-environment.md` | ops | deploy | reference |
| `02-deploy.md` | ops | deploy | guide |
| `03-celery.md` | ops | celery | guide |
| `04-migrations.md` | ops | database | guide |
| `05-management-commands.md` | ops | deploy | reference |
| `06-oidc-nc.md` | ops | nc | guide |
| `07-troubleshooting.md` | ops | overview | troubleshooting |

### 批量打标签操作

1. 先在「元数据」管理界面创建 `audience` / `module` / `doc_type` 三个字符串字段。
2. 回到文档列表，按目录批量勾选：
   - 勾选 `user-guide/` 全部 21 篇 → 编辑元数据 → `audience=user`。
   - 勾选 `developer-guide/` 全部 10 篇 → `audience=developer`。
   - 勾选 `ops-guide/` 全部 7 篇 → `audience=ops`。
3. 再按 module 二次批量勾选（如 ads 相关的 `05-ads-sp.md` + `06-ads-tools-strategy.md` → `module=ads`）。
4. 最后标 doc_type（排障篇 → `troubleshooting`；接口篇 → `reference`；其余 → `guide`）。
5. 在 AI 助手应用的「上下文」配置里启用「元数据筛选」。

### 新增文档时的标签规则

新增文档时按下表确定标签：

| 判定 | 标签 |
| --- | --- |
| 文档在 `user-guide/` | `audience=user` |
| 文档在 `developer-guide/` | `audience=developer` |
| 文档在 `ops-guide/` | `audience=ops` |
| 内容是操作步骤 / 使用说明 | `doc_type=guide` |
| 内容是接口 / 字段 / 命令清单 | `doc_type=reference` |
| 内容是问题排查 / 报错处理 | `doc_type=troubleshooting` |
| module 取文档对应的业务模块名 | 见上表 module 列 |
