"""AI 消息 SSE 订阅视图（ai_stream_view）。

设计要点：
    - WSGI 同步生成器 + StreamingHttpResponse，无需 ASGI 改造
    - 订阅端必发流程：先回放 DB 已落字 → 再阻塞订阅 Redis 频道
    - 阻塞 ``pubsub.listen()`` 会吃 worker，但 ERP 内部并发量 ≤20 路完全可接受
    - 30 秒心跳防止中间代理（nginx / 浏览器）超时断连
    - 终止条件：收到 done 事件 / 消息状态已是终态 / 心跳超时
"""

import json
import logging
import time
from typing import Iterator

from django.http import StreamingHttpResponse
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    renderer_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request
from rest_framework.response import Response

from apps.system.auth.bearer_token_auth import BearerTokenAuthentication
from apps.ai.models.message import AiMessage, MessageStatus, MessageType
from apps.system.permissions.v2_access import IsV2Accessible
from apps.ai.utils.redis_channel import (
    EVENT_DONE,
    EVENT_PLAN,
    EVENT_TOKEN,
    build_channel,
    get_redis_client,
)

logger = logging.getLogger(__name__)


# 心跳间隔（秒）：在没有真实事件流过时定期发注释帧，防止反向代理断开空闲连接
_HEARTBEAT_INTERVAL = 25

# 单次订阅最长生命周期（秒）：超过即主动收尾，让前端发起新订阅
# 避免任务异常未发 done 时 worker 被永久占用
_MAX_SUBSCRIBE_SECONDS = 600

# 终态集合：消息处于这些状态时无需订阅 Redis，直接返回 done
_TERMINAL_STATUSES = {
    MessageStatus.DONE,
    MessageStatus.FAILED,
    MessageStatus.CANCELLED,
}


def _format_sse(event: str, data: dict) -> str:
    """组装符合 SSE 协议的单条事件帧。

    Args:
        event (str): 事件类型，对应前端 ``addEventListener(event, ...)`` 的事件名。
        data (dict): 事件负载，会被 JSON 序列化。

    Returns:
        str: ``event: xxx\\ndata: {...}\\n\\n`` 格式字符串。
    """
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


def _format_heartbeat() -> str:
    """组装 SSE 心跳帧（注释行，浏览器静默忽略，不触发事件回调）。"""
    return f': heartbeat {int(time.time())}\n\n'


class _SSEEventStreamRenderer(BaseRenderer):
    """SSE 内容协商兜底 renderer。

    DRF 默认只能渲染 application/json，前端发 ``Accept: text/event-stream`` 时
    会被 DRF 内容协商拒绝并返回 406。注册本 renderer 让 DRF 知道"我能产出这个 MIME"，
    实际响应仍由视图通过 ``StreamingHttpResponse`` 直接构造，不会走 renderer 的 ``render()``。
    """

    media_type = 'text/event-stream'
    format = 'sse'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # 视图直接返回 StreamingHttpResponse，不经此处；保留空实现以满足 BaseRenderer 接口
        return data if isinstance(data, (bytes, str)) else b''


@api_view(['GET'])
@authentication_classes([BearerTokenAuthentication, OAuth2Authentication])
@permission_classes([IsAuthenticated, IsV2Accessible])
@renderer_classes([_SSEEventStreamRenderer])
def subscribe_message(request: Request, public_id):
    """订阅指定 AI 消息的 SSE 实时流。

    完整流程：
        1. 校验消息归属当前用户（按 public_id 查询），否则 404
        2. 回放 DB 中 ``content`` 已落部分（解决"刷新页面回来"场景）
        3. 若 ``raw_plan_json`` 已存在则补播 plan 事件
        4. 若状态已是终态，立刻发 done 后退出
        5. 否则订阅 Redis Pub/Sub 频道，阻塞接收并转发到 SSE
        6. 心跳 / 超时 / done 任一条件触发即退出

    Args:
        request (Request): DRF 请求对象。
        public_id: AiMessage 对外 UUID（由 URL 路由从 ``<uuid:public_id>`` 解析）。

    Returns:
        StreamingHttpResponse: SSE 流响应。

    Raises:
        无显式抛出；所有错误转为 SSE error 帧或 HTTP 状态码。
    """
    # 单点查询用于鉴权与状态判断；不能放入生成器，否则 worker 进入流后无法返回 HTTP 状态码
    try:
        message = AiMessage.objects.select_related('conversation').get(
            public_id=public_id,
            conversation__user=request.user,
        )
    except AiMessage.DoesNotExist:
        return Response({'detail': '消息不存在或无权访问'}, status=404)

    response = StreamingHttpResponse(
        _stream_iter(message),
        content_type='text/event-stream; charset=utf-8',
    )
    # 关键 header：禁止任何中间层缓冲，否则前端只能等流结束才能看到内容
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'  # nginx 关闭 buffer
    response['Connection'] = 'keep-alive'
    return response


def _stream_iter(message: AiMessage) -> Iterator[str]:
    """SSE 流生成器：先回放历史，再订阅 Redis 实时事件。

    Args:
        message (AiMessage): 已鉴权的目标消息。

    Yields:
        str: SSE 协议格式的事件帧。
    """
    message_id = message.id
    log_prefix = f'[ai_stream_view][_stream_iter] msg={message_id}'

    # ---- 阶段 1：回放已落库内容 ----
    if message.content:
        yield _format_sse(EVENT_TOKEN, {'text': message.content, 'replay': True})

    if message.message_type == MessageType.PLAN and message.raw_plan_json:
        yield _format_sse(EVENT_PLAN, message.raw_plan_json)

    # ---- 阶段 2：消息已是终态，无需进入订阅 ----
    if message.status in _TERMINAL_STATUSES:
        yield _format_sse(EVENT_DONE, {'final_status': message.status})
        return

    # ---- 阶段 3：订阅 Redis 频道 ----
    try:
        redis_client = get_redis_client()
    except Exception as exc:
        logger.error('%s 获取 Redis 失败: %s', log_prefix, str(exc), exc_info=True)
        yield _format_sse('error', {'code': 'REDIS_UNAVAILABLE', 'message': str(exc)})
        yield _format_sse(EVENT_DONE, {})
        return

    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    channel = build_channel(message_id)

    try:
        pubsub.subscribe(channel)
        deadline = time.time() + _MAX_SUBSCRIBE_SECONDS

        while time.time() < deadline:
            # get_message + timeout 实现非阻塞轮询，便于发心跳
            raw = pubsub.get_message(timeout=_HEARTBEAT_INTERVAL)
            if raw is None:
                # 没有新事件 → 发心跳
                yield _format_heartbeat()
                continue

            if raw.get('type') != 'message':
                continue

            try:
                envelope = json.loads(raw.get('data') or '{}')
            except json.JSONDecodeError:
                logger.warning('%s 跳过非法 Pub/Sub 帧', log_prefix)
                continue

            event_type = envelope.get('type', '')
            payload = envelope.get('payload', {})

            yield _format_sse(event_type, payload)

            if event_type == EVENT_DONE:
                logger.info('%s 收到 done，订阅退出', log_prefix)
                return

        # 超过最长订阅时长仍未结束：主动收尾，前端可重新订阅
        logger.warning('%s 订阅达到最长时长 %ss，主动收尾', log_prefix, _MAX_SUBSCRIBE_SECONDS)
        yield _format_sse(EVENT_DONE, {'reason': 'subscribe_timeout'})

    finally:
        try:
            pubsub.close()
        except Exception:
            pass
