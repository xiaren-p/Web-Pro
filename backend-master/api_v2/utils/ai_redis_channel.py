"""AI 实时广播 Redis 频道工具（ai_redis_channel）。

封装 Plan Mode 流式对话所需的 Redis Pub/Sub 频道命名与消息序列化逻辑。
该模块是 Celery 任务（生产侧）与 SSE 订阅视图（消费侧）之间的事件总线契约层。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


# 频道命名规范：ai:msg:<message_id>
# 选用 "ai:" 前缀以便与项目其他 Redis 用途（缓存、Celery broker）通过 SCAN/MONITOR 区分。
_CHANNEL_PREFIX = 'ai:msg:'

# 事件类型：与前端 useAiChatStream 回调一一对应
EVENT_TOKEN = 'token'
EVENT_PLAN = 'plan'
EVENT_MESSAGE_META = 'message_meta'
EVENT_ERROR = 'error'
EVENT_DONE = 'done'


def build_channel(message_id: int) -> str:
    """根据消息 ID 构造 Redis Pub/Sub 频道名。

    Args:
        message_id (int): AiMessage 主键 ID。

    Returns:
        str: 频道字符串，例如 ``ai:msg:42``。
    """
    return f'{_CHANNEL_PREFIX}{message_id}'


def get_redis_client() -> redis.Redis:
    """获取共享 Redis 客户端。

    复用项目 ``REDIS_URL`` 配置；不依赖 django-redis 缓存接口，因为本模块需要
    Pub/Sub 原生能力（``publish`` / ``pubsub``），而 django-redis 上层封装并未暴露 ``pubsub`` API。

    Returns:
        redis.Redis: 已就绪的 Redis 连接实例。

    Raises:
        RuntimeError: 当 settings.REDIS_URL 未配置时抛出，避免静默回退到本地 6379。
    """
    redis_url: str = getattr(settings, 'REDIS_URL', '') or ''
    if not redis_url:
        raise RuntimeError(
            '[ai_redis_channel][get_redis_client] settings.REDIS_URL 未配置，'
            'AI Pub/Sub 功能依赖 Redis，请先在 .env 中提供 REDIS_URL。'
        )

    # decode_responses=True：让 publish/listen 直接收发字符串，避免每次手动 decode。
    return redis.from_url(redis_url, decode_responses=True)


def publish_event(redis_client: redis.Redis, message_id: int, event_type: str, payload: dict[str, Any]) -> None:
    """向指定消息频道广播一条事件。

    选择 publish + listen 而非 Streams 的原因：
        Plan Mode 对历史回放需求由 DB 承担（``content`` 字段 + ``raw_plan_json``），
        Pub/Sub 只服务"实时增量推送"，不需要持久化 / 消费组语义，越简单越好。

    Args:
        redis_client (redis.Redis): 调用方持有的连接（避免每次 publish 都新建）。
        message_id (int): 目标 AiMessage 主键。
        event_type (str): 事件类型，必须是 ``EVENT_*`` 常量之一。
        payload (dict[str, Any]): 事件负载，会被 JSON 序列化后落入频道。
    """
    channel = build_channel(message_id)
    body = json.dumps({'type': event_type, 'payload': payload}, ensure_ascii=False)
    try:
        redis_client.publish(channel, body)
    except redis.RedisError as exc:
        logger.error(
            '[ai_redis_channel][publish_event] 广播失败: channel=%s event=%s err=%s',
            channel,
            event_type,
            str(exc),
            exc_info=True,
        )
        raise
