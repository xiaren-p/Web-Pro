# Celery worker 与 beat

## 启动 Worker

**必须显式列出所有队列**，否则未列出的队列任务永远不执行：

```bash
cd backend-master
celery -A backend_master worker -l info -Q celery,parallel_queue,single_thread_queue
```

## 启动 Beat

```bash
celery -A backend_master beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 三队列并发

| 队列 | 并发 | 用途 |
| --- | --- | --- |
| `celery` | 默认（4） | 轻量、定时、低频 |
| `parallel_queue` | 4 | AI 对话、可并发批量 |
| `single_thread_queue` | 1 | 写同资源、外部 API QPS 限制、串行任务 |

> `CLAUDE.md` §6.8 描述的 3 个 systemd service（`celery-default` / `celery-parallel` / `celery-single`，并发 4/8/1）属运维端部署形态，仓库内无法验证，以实际服务器 `-Q` 配置为准。

## 为什么必须拆 service

单 service 用 `-c 8` 时，`single_thread_queue` 任务也会被 8 个并发槽中任意一个取走，「严格串行」语义失效。只有「1 个 service + concurrency=1 + 只监听 single_thread_queue」才能保证真正串行。

## Beat 调度项

当前定时任务（`CELERY_BEAT_SCHEDULE`）：

| 名称 | 任务 | 周期 |
| --- | --- | --- |
| `qinglong-env-sync` | 青龙环境变量同步 | 每 600 秒 |
| `nc-process-pending` | NC 同步处理 | 每 30 秒 |
| `nc-retry-failed` | NC 同步重试 | 每 300 秒 |
| `cleanup-orphan-uploads` | 清理孤儿上传 | 每天 03:00 |
| `listing-tag-sync` | 标签同步 | 每 5 秒（expires=4） |
| `listing-tag-modify` | 标签绑定修改 | 每 5 秒（expires=4） |

## 高频任务防堆积

schedule ≤ 60 秒的 Beat 任务必须加 `options.expires` 且 `expires < schedule`，否则任务跑慢时 Beat 持续堆积。`listing-tag-sync` / `listing-tag-modify` 已配置（schedule=5, expires=4）。

## 新增任务后必须重启

- 改 `CELERY_TASK_ROUTES` → **重启 Django Web**（路由表是 Django 派发时读的）。
- 新增任务文件 / 改 `tasks/__init__.py` → **重启目标队列的 worker**（worker 启动时才扫描 `tasks/__init__.py`）。

## 排查

| 现象 | 排查 |
| --- | --- |
| `Received unregistered task` | 重启目标队列 worker |
| 任务跑去错的队列 | 检查 `CELERY_TASK_ROUTES` key 与装饰器 `name` 是否一致 |
| Redis 堆积没人取 | `redis-cli LLEN <队列名>`；检查 worker 的 `-Q` 是否包含该队列 |
| 改完路由没生效 | 重启 Django Web（不是 worker） |
