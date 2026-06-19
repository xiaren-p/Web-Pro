# Celery 任务体系

本文详述 Celery 任务的队列、路由、加锁与新增流程。

## 三队列与并发

| 队列 | 并发 | 适用场景 |
| --- | --- | --- |
| `celery` | 默认（4） | 轻量、定时、低频任务 |
| `parallel_queue` | 4 | 可并发的批量任务、AI 对话 |
| `single_thread_queue` | 1 | 须串行、写同资源、调有 QPS 限制的外部 API |

## 现有任务清单

| 任务 name | 队列 | 说明 |
| --- | --- | --- |
| `api_v2.tasks.ai_chat_task.run_ai_chat_task` | parallel_queue | AI 对话流式生成 |
| `api_v2.tasks.ad_campaign_submit_task.submit_pending_campaigns_task` | single_thread_queue | 广告活动提交 |
| `api_v2.tasks.ad_time_pricing_task.run_ad_time_pricing_task` | single_thread_queue | 分时策略命中 |
| `api_v2.tasks.time_pricing_task.run_time_pricing_task` | single_thread_queue | 分时调价执行 |
| `api_v2.tasks.bid_adjustment_task.run_bid_adjustment_task` | single_thread_queue | 竞价调整 |
| `api_v2.tasks.campaign_adjustment_task.run_campaign_adjustment_task` | single_thread_queue | 活动调整 |
| `api_v2.tasks.optimization_strategy_task.run_optimization_strategy_task` | single_thread_queue | 优化策略匹配 |
| `api_v2.tasks.optimization_execution_task.run_optimization_execution_task` | single_thread_queue | 优化策略执行 |
| `api_v2.tasks.listing_image_upload_task.upload_listing_images_task` | single_thread_queue | Listing 图片上传 |
| `api_v2.tasks.listing_tag_sync_task.run_listing_tag_sync_task` | single_thread_queue | 标签同步（Beat 5s，expires=4） |
| `api_v2.tasks.listing_tag_modify_task.run_listing_tag_modify_task` | single_thread_queue | 标签绑定修改（Beat 5s，expires=4） |
| `api_v2.tasks.qinglong_env_sync_task.sync_qinglong_env_sync_task` | celery | 青龙环境变量同步（Beat 600s） |
| `api_v1.tasks.nc_sync_tasks.process_pending_nc_tasks` | celery | NC 同步处理（Beat 30s） |
| `api_v1.tasks.nc_sync_tasks.retry_failed_nc_tasks` | celery | NC 同步重试（Beat 300s） |
| `api_v1.tasks.maintenance_tasks.cleanup_orphan_uploads` | celery | 清理孤儿上传（每天 03:00） |

## 路由表

路由唯一声明位置：`backend_master/settings.py` 的 `CELERY_TASK_ROUTES`。**禁止**在 `@shared_task` 写 `queue=`，**禁止**调用方 `apply_async(queue=...)` 绕过路由表。

## 新增任务标准 5 步（漏一步即任务静默不执行）

1. 写任务文件 `api_v2/tasks/xxx_task.py`（或 `api_v1/tasks/`），`@shared_task` 的 `name=` 必须 = 完整模块路径，**禁止**省略 `name=`，**禁止**写 `queue=`。
2. 在 `api_v2/tasks/__init__.py`（或 `api_v1/tasks/__init__.py`）**显式 `import` 该任务并加入 `__all__`**——不注册则 worker 启动时不加载，派发报 `Received unregistered task` 然后被丢弃。
3. 在 `settings.CELERY_TASK_ROUTES` 追加一行，key 与装饰器 `name` 一字不差，按决策树选队列。
4. **重启 Django Web**（路由表是 Django 派发时读的）。
5. **重启目标队列的 Celery worker**（worker 启动时才扫描 `tasks/__init__.py`）。

## 任务加锁（`api_v2/utils/task_execution_lock.py`）

唯一合法的 Celery 任务加锁方案，三层防御必须全到位：

1. **队列层**：`single_thread_queue` concurrency=1（物理串行）。
2. **任务体**：`with TaskExecutionLock(LOCK_KEY, ttl=LOCK_TTL) as acquired:`。
3. **视图层**：`if is_task_running(LOCK_KEY): return Response(BUSY_RESPONSE(...), status=409)`。

硬规则：

- 视图禁止 `cache.add` 写锁（只能 `is_task_running` 读）。
- `LOCK_KEY` 必须由任务模块导出，视图 `from import` 复用。
- `LOCK_TTL ≥ time_limit + 60`。
- `acks_late=True` 必须开。
- 抢锁失败必须返回 schema 完整 dict（如 `{"processed": 0, "errors": [...]}`）。
- 409 必须用 `BUSY_RESPONSE`（错误码 `B0001`）。

## 纯 Beat 高频任务（无 HTTP 视图）

schedule ≤ 60s 必须加 `options.expires` 且 `expires < schedule`，防止 Beat 堆积。参考 `listing_tag_sync`（schedule=5, expires=4）。

## 选队列决策树

```text
任务耗时？
   < 30s → celery
   ≥ 30s → 能并发吗？
      能 → parallel_queue
      不能（写同资源 / 外部 API QPS 限制） → single_thread_queue
```
