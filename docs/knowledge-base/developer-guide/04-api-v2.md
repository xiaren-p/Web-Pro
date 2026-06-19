# api_v2 接口总览

`api_v2` 承载工作流任务调度与异步执行，路由在 `backend-master/api_v2/urls.py`，根路径 `/api/v2/`。鉴权支持 Bearer Token（前端用户）与 OAuth2 Client Credentials（外部应用，scope `api_v2`）双路。响应格式与 `api_v1` 一致。

## 工作流接口（`/workflow/*`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/workflow/` | POST | 启动工作流任务 |
| `/workflow/<id>/` | GET | 查询任务状态 |
| `/workflow/<id>/cancel/` | POST | 取消任务 |

## 开发者应用接口（`/developer/apps/*`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/developer/apps` | GET / POST | 应用列表 / 新建（生成 client_id + client_secret） |
| `/developer/apps/<id>/` | DELETE | 删除应用 |
| `/developer/apps/<id>/rotate-secret/` | POST | 轮换密钥（旧 secret 立即失效） |

`client_secret` 明文存储（`CLIENT_SECRET_HASHED=False`），便于排查 `invalid_client`。

## 广告执行接口（`/ads/*`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/ads/upload` | POST | 上传广告活动 xlsx（multipart，含竞价参数 + 国家预算 JSON） |
| `/ads/queue` | GET | 上传队列分页（parse_status/date_start/date_end/shop/country/user_id） |
| `/ads/queue/bulk-delete` | DELETE | 批量删除（body: ids[]） |
| `/ads/queue/retry` | POST | 重试（FAILED/ANOMALY → PENDING，断点续跑） |
| `/ads/submit` | POST | **手动同步触发**批量提交领星（当前实际提交路径） |
| `/ads/time-pricing/execute/` | POST | 手动触发分时调价 |
| `/ads/bid-adjustment/run/` | POST | 手动触发竞价调整 |
| `/ads/campaign-adjustment/run/` | POST | 手动触发活动调整 |
| `/ads/optimization-strategy/run/` | POST | 手动触发优化策略匹配 |
| `/ads/optimization-strategy/execute/` | POST | 手动触发优化策略执行 |

队列状态枚举：`0`FAILED / `1`PENDING / `2`SUCCESS / `3`ANOMALY。PENDING 置顶。普通用户仅看自己的，管理员可查看所有人的。

> ⚠️ `submit_pending_campaigns_task` 虽注册了 Celery 路由，但**未在 Beat 调度中注册**，不会自动定时提交。实际靠 HTTP `/ads/submit/` 手动同步触发。

执行类接口在任务运行中再次调用返回 409（`B0001` 任务正在执行中），由 `BUSY_RESPONSE` 生成。

## AI 对话接口（`/ai/*`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/ai/chat/` | POST | 提交问题，返回 `conversation_id/user_message_id/assistant_message_id/task_id`（202） |
| `/ai/stream/<uuid:public_id>/` | GET | SSE 订阅消息流（回放 DB → Redis Pub/Sub 转发，25s 心跳，600s 最长） |
| `/ai/conversations/` | GET | 会话列表（置顶优先 + updated_at 倒序，前 100） |
| `/ai/conversations/search/` | GET | 全文搜索（`?q=`，标题 + 消息内容双优先级，带 snippet） |
| `/ai/conversations/<id>/messages/` | GET | 历史消息回放 |
| `/ai/conversations/<id>/rename/` | PATCH | 重命名 |
| `/ai/conversations/<id>/pin/` | PATCH | 置顶 / 取消 |
| `/ai/conversations/<id>/` | DELETE | 删除会话（级联消息） |
| `/ai/conversations/<id>/move/` | PATCH | 移动到分组 |
| `/ai/messages/<id>/cancel/` | POST | 取消生成（Celery revoke + 广播 done） |
| `/ai/groups/` | GET / POST | 分组列表 / 新建 |
| `/ai/groups/reorder/` | PATCH | 分组排序 |
| `/ai/groups/<id>/` | DELETE | 删除分组（会话归为未分组） |
| `/ai/groups/<id>/rename/` | PATCH | 重命名分组 |

对外一律 `public_id`（UUID），内部 int 主键不暴露。SSE 事件类型：`EVENT_TOKEN` / `EVENT_PLAN` / `EVENT_DONE` / `EVENT_ERROR` / `EVENT_MESSAGE_META`。

## 409 冲突响应

```json
{ "code": "B0001", "data": null, "msg": "xxx 任务正在执行中" }
```

由 `BUSY_RESPONSE` 生成，前端统一处理。
