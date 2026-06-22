# 常见问题排查

## 后端起不来

| 现象 | 排查 |
| --- | --- |
| 启动报错找不到 `.env` | `backend-master/.env` 必需且被 gitignore，需手动创建，见 `01-environment.md` |
| `FERNET_SECRET_KEY` 未配置 | Config PASSWORD 类型无法加解密，生成命令见 `01-environment.md` |
| `DIFY_API_BASE` / `DIFY_API_KEY` 未配置 | AI 助手不可用，`DifyClient` 初始化抛 `RuntimeError` |
| OIDC 不工作 | 检查 `backend_master/oidc_private.pem` 是否存在，不存在执行 `generate_oidc_key` |
| MySQL 连接失败 | 检查 `DB_*` 环境变量、MySQL 服务状态、`utf8mb4` 字符集 |

## Celery 任务问题

| 现象 | 排查 |
| --- | --- |
| `Received unregistered task` | 新任务未在 `tasks/__init__.py` 注册，或 worker 未重启 |
| 任务永远不执行 | worker 启动未列全 `-Q` 队列，必须 `celery,parallel_queue,single_thread_queue` |
| 改完路由没生效 | 只重启 worker 不够，必须**重启 Django Web**（路由表是 Django 派发时读的） |
| Redis 堆积 | `redis-cli LLEN <队列名>` 看堆积；检查 worker 的 `-Q` 是否包含该队列 |
| 高频 Beat 任务堆积 | schedule ≤ 60s 必须加 `options.expires` 且 < schedule |
| 任务重复执行 | 检查是否加锁（三层防御）；`single_thread_queue` concurrency 是否=1 |

## AI 助手问题

| 现象 | 排查 |
| --- | --- |
| AI 不回复 | 检查 `DIFY_API_BASE` / `DIFY_API_KEY`；Celery `parallel_queue` worker 是否运行 |
| 流式输出中断 | SSE 订阅先回放 DB 已落内容；检查 Redis 是否可用；`X-Accel-Buffering: no` 是否透传 |
| Plan 卡片不显示 | 后端 `plan_translator` 未提取到 `<plan>` JSON；检查 LLM 提示词 |
| 取消无效 | `/ai/messages/<id>/cancel/` 调 Celery revoke；任务可能已接近完成 |
| 切换应用后消息发到旧应用 | Dify `conversation_id` 不可跨应用复用；续接会话时后端忽略前端 `app_code`，沿用会话已绑定的 `dify_app`。切换应用必须新建会话 |
| `DifyApp` 缺少默认应用 | `DifyApp.objects.get_default()` 抛 `DoesNotExist`；通过 `manage.py shell` 创建至少一条 `is_active=True` 的 `DifyApp` 记录 |
| Dify API Key 解密失败 | 检查 `FERNET_SECRET_KEY` 是否与加密时一致；`api_key_encrypted` 是否为空；用 `DifyApp.encrypt_api_key()` 重新加密写入 |

## 前端问题

| 现象 | 排查 |
| --- | --- |
| `npm install` 失败 | 必须用 pnpm（`preinstall` 拦截 npm/yarn） |
| 接口 404 | 检查 `/dev-api` 代理配置（`vite.config.ts`）；后端是否启动 |
| 类型错误 | `pnpm run type-check`（命令是 `type-check` 不是 `typecheck`） |
| lint 失败 | `pnpm run lint:eslint`；禁 `@ts-ignore` / `eslint-disable` 掩盖 |
| commit 被拒 | commitlint 强制 Conventional Commits，type 枚举：`feat\|fix\|docs\|style\|refactor\|perf\|test\|build\|ci\|revert\|chore\|wip` |

## 鉴权问题

| 现象 | 排查 |
| --- | --- |
| `CSRF token missing` | DRF 走 Bearer 不需要 CSRF；若出现说明退化为 Session 鉴权（Bearer 已过期），检查 `BearerTokenAuthentication` 是否仍是唯一认证类 |
| `invalid_client` | `client_secret` 不匹配；`CLIENT_SECRET_HASHED=False` 明文存储便于排查；变更后执行 `setup_nc_oidc_client --reset-secret` |
| 401 token 过期 | 用 `refresh_token` 调 `/auth/refresh-token`；前端有自动刷新逻辑 |
| 外部应用调 api_v2 403 | 检查 OAuth2 scope 是否为 `api_v2` |

## 数据库问题

| 现象 | 排查 |
| --- | --- |
| Doris 查询失败 | Doris 为只读分析库，检查 `DORIS_*` 环境变量；`analytics` 库不参与迁移 |
| 迁移冲突 | 见 `04-migrations.md`；`--fake` 或手动 SQL 补救 |
| `managed=False` 表不存在 | 领星同步只读表需手动 SQL 建表，参考 `scripts/` 下 SQL |

## Nextcloud 同步问题

| 现象 | 排查 |
| --- | --- |
| NC 同步不跑 | `nc-process-pending` Beat 任务是否运行；`celery` 队列 worker 是否启动 |
| NC 用户 / 群组不一致 | 执行 `python manage.py reconcile_nc` 全量对账 |
| NC 头像不同步 | `sync_nc_avatars` 或 `reset_user_avatars` |
| NC SSO 跳转丢 session | `SESSION_COOKIE_SAMESITE=None` + `SESSION_COOKIE_SECURE=True`（HTTPS） |

## 亏损订单数据问题

| 现象 | 排查 |
| --- | --- |
| 数据不更新 | `lossmakingorders_sync` 当前是 no-op（空操作），不触发领星拉取；`MonthlyLossOrder` / `MonthlyLossOrderFirst20` 数据由外部注入（admin 手工或 ETL），系统内无写入代码 |
| 缓存过期 | `OrderProfitCache` 已废弃，`prune_orderprofitcache` 命令属遗留（`--minutes N` 清理超 TTL，默认 10 分钟，`--dry-run` 预览） |
| 前 20 天口径 | `MonthlyLossOrderFirst20` 仅存每月 1-20 日数据，下载对比取「本月前 20 天 vs 上月整月」 |

## 仪表盘问题

| 现象 | 排查 |
| --- | --- |
| 仪表盘数据全为 0 / 占位 | 当前仪表盘 7 个组件（库存 / 广告 / 销量 / 补货 / 评论 / 利润 / 绩效）为硬编码 Mock，尚未接入后端 API；仅天气为真实数据 |
| 没有「店铺切换 / 日期范围 / 刷新」 | DashboardHeader 当前未实现这三项功能 |

## 广告提交问题

| 现象 | 排查 |
| --- | --- |
| 广告上传后不提交 | `submit_pending_campaigns_task` 未被 Beat 调度，需手动点「提交」触发 HTTP `/api/v2/ads/submit/` |
| 提交返回 409 | 任务正在执行中（`B0001`），等待完成后再试 |
| 提交部分失败 | 队列状态 `ANOMALY`（部分成功），可点「重试」断点续跑（跳过已完成步骤） |

## 图片上传问题

| 现象 | 排查 |
| --- | --- |
| 图片上传接口无鉴权 | `ImageUploadViewSet` 权限为 `AllowAny`，属已知风险点 |
| 同步后 status 不变 | `sync` / `batch_sync` 仅追加 log，不修改 status；status 需外部回调或手动维护 |
| CSV 导入失败 | 检查编码（UTF-8 BOM 优先 / GBK 兜底）+ 必需列（`图片组` 或 `imageGroup`） |

## 配置问题

| 现象 | 排查 |
| --- | --- |
| 刷新缓存无效 | `/configs/refresh-cache` 当前为占位实现，直接返回成功无实际操作 |
| PASSWORD 类型无法加解密 | 检查 `.env` 中 `FERNET_SECRET_KEY` 是否配置 |
| 配置编辑按钮不显示 | 前端权限码 `sys:config:update` 与后端 `sys:config:edit` 可能不一致，核对菜单 perms |
