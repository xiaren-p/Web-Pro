"""AI 对话视图（ai_chat_view）：非流式接口集合。

职责：
    - POST   /chat/                                  提交问题，入队 Celery 任务，返回消息 ID（不等流）
    - GET    /conversations/                         当前用户会话列表（含分组、置顶字段）
    - GET    /conversations/search/?q=               全文搜索会话标题与消息内容
    - GET    /conversations/<id>/messages/           拉取某会话的全部消息（刷新回放）
    - PATCH  /conversations/<id>/rename/             重命名会话
    - PATCH  /conversations/<id>/pin/                置顶 / 取消置顶
    - DELETE /conversations/<id>/                    删除会话（级联消息）
    - POST   /messages/<id>/cancel/                  取消正在生成的消息
SSE 流式订阅请见 ``ai_stream_view`` 模块。
"""

import logging

from django.db import models
from django.utils import timezone
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from apps.system.auth.bearer_token_auth import BearerTokenAuthentication
from apps.ai.models.conversation import AiConversation
from apps.ai.models.message import AiMessage, MessageStatus
from apps.system.permissions.v2_access import IsV2Accessible
from apps.ai.serializers.chat_serializer import (
    AiChatRequestSerializer,
    AiConversationSerializer,
    AiMessageSerializer,
)
from apps.ai.services.chat_service import AiChatService

logger = logging.getLogger(__name__)


_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]


@api_view(['POST'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def start_chat(request: Request) -> Response:
    """提交一轮对话，立即返回消息 ID，真实生成在 Celery 后台运行。

    前端拿到返回值后应立刻发起 ``GET /api/v2/ai/stream/<assistant_message_id>/`` 订阅 SSE。
    刷新页面 / 切换标签 / 离开后回来均可再次订阅同一条消息，不会丢失进度。
    """
    serializer = AiChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    try:
        result = AiChatService().start_chat(
            user=request.user,
            query=payload['query'],
            conversation_id=payload.get('conversation_id'),
            app_code=payload.get('app_code') or None,
            inputs=payload.get('inputs') or {},
        )
    except ValueError as exc:
        logger.warning('[ai_chat_view][start_chat] 业务校验失败: %s', str(exc))
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        logger.error('[ai_chat_view][start_chat] 入队失败: %s', str(exc), exc_info=True)
        return Response(
            {'detail': 'AI 服务暂不可用，请稍后重试'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            'conversation_id': result.conversation_id,
            'user_message_id': result.user_message_id,
            'assistant_message_id': result.assistant_message_id,
            'task_id': result.celery_task_id,
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(['GET'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def list_conversations(request: Request) -> Response:
    """返回当前用户的会话列表。

    排序规则：置顶的优先（按 ``pinned_at`` 倒序），然后非置顶按 ``updated_at`` 倒序。
    默认返回前 100 条。
    """
    queryset = (
        AiConversation.objects.filter(user=request.user)
        .order_by(
            models.F('pinned_at').desc(nulls_last=True),
            '-updated_at',
        )[:100]
    )
    data = AiConversationSerializer(queryset, many=True).data
    return Response({'items': data})


@api_view(['GET'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def list_messages(request: Request, public_id) -> Response:
    """返回某会话下的全部消息正文（用于刷新页面后的历史回放）。

    Args:
        request (Request): DRF 请求。
        public_id: 会话对外 UUID（由 URL 路由从 ``<uuid:public_id>`` 解析）。
    """
    try:
        conversation = AiConversation.objects.get(public_id=public_id, user=request.user)
    except AiConversation.DoesNotExist:
        return Response({'detail': '会话不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)

    messages = AiMessage.objects.filter(conversation=conversation).order_by('created_at')
    data = AiMessageSerializer(messages, many=True).data
    return Response({'items': data})


@api_view(['DELETE'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def delete_conversation(request: Request, public_id) -> Response:
    """删除会话及其所有消息（级联）。

    Args:
        request (Request): DRF 请求。
        public_id: 会话对外 UUID。
    """
    deleted, _ = AiConversation.objects.filter(public_id=public_id, user=request.user).delete()
    if not deleted:
        return Response({'detail': '会话不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'success': True})


@api_view(['PATCH'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def rename_conversation(request: Request, public_id) -> Response:
    """重命名会话标题。

    Args:
        request (Request): DRF 请求，body 需包含 ``title`` 字段。
        public_id: 会话对外 UUID。

    Returns:
        Response 200: {"success": true, "title": "新标题"}
        Response 400: title 缺失或为空
        Response 404: 会话不存在或无权访问
    """
    title = (request.data or {}).get('title', '').strip() if request.data else ''
    if not title:
        return Response({'detail': '标题不能为空'}, status=status.HTTP_400_BAD_REQUEST)
    if len(title) > 200:
        return Response({'detail': '标题不能超过 200 字'}, status=status.HTTP_400_BAD_REQUEST)

    updated = AiConversation.objects.filter(
        public_id=public_id,
        user=request.user,
    ).update(title=title)

    if not updated:
        return Response({'detail': '会话不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'success': True, 'title': title})


@api_view(['PATCH'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def pin_conversation(request: Request, public_id) -> Response:
    """置顶 / 取消置顶会话。

    Body: {"pinned": true | false}
    pinned=true：写入当前时间到 ``pinned_at``；
    pinned=false：将 ``pinned_at`` 置为 NULL。

    Args:
        request (Request): DRF 请求。
        public_id: 会话对外 UUID。
    """
    body = request.data or {}
    pinned = bool(body.get('pinned', False))

    target_value = timezone.now() if pinned else None
    updated = AiConversation.objects.filter(
        public_id=public_id,
        user=request.user,
    ).update(pinned_at=target_value)

    if not updated:
        return Response({'detail': '会话不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'success': True, 'pinned': pinned})


@api_view(['GET'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def search_conversations(request: Request) -> Response:
    """全文搜索：匹配会话标题 OR 消息内容。

    Query params:
        q (str): 搜索关键词（必填）。
        limit (int): 最多返回多少条命中（默认 30，上限 100）。

    Returns:
        Response 200: {"items": [{conversation_id, conversation_title, message_id?, role?, snippet, matched_at}, ...]}
    """
    keyword = (request.query_params.get('q') or '').strip()
    if not keyword:
        return Response({'items': []})
    if len(keyword) > 100:
        return Response({'detail': '关键词过长'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        limit = min(int(request.query_params.get('limit') or 30), 100)
    except (TypeError, ValueError):
        limit = 30

    user = request.user
    hits: list[dict] = []
    seen_conversation_ids: set = set()

    # 优先级 1：会话标题命中
    title_hits = AiConversation.objects.filter(
        user=user,
        title__icontains=keyword,
    ).order_by(
        models.F('pinned_at').desc(nulls_last=True),
        '-updated_at',
    )[:limit]

    for conv in title_hits:
        hits.append({
            'conversation_id': str(conv.public_id),
            'conversation_title': conv.title or '新对话',
            'message_id': None,
            'role': None,
            'snippet': conv.title or '',
            'matched_at': conv.updated_at,
        })
        seen_conversation_ids.add(conv.id)

    # 优先级 2：消息内容命中（剩余配额）
    remaining = limit - len(hits)
    if remaining > 0:
        message_hits = (
            AiMessage.objects.filter(
                conversation__user=user,
                content__icontains=keyword,
            )
            .exclude(conversation_id__in=seen_conversation_ids)
            .select_related('conversation')
            .order_by('-created_at')[:remaining]
        )

        for msg in message_hits:
            snippet = _make_snippet(msg.content, keyword)
            hits.append({
                'conversation_id': str(msg.conversation.public_id),
                'conversation_title': msg.conversation.title or '新对话',
                'message_id': str(msg.public_id),
                'role': msg.role,
                'snippet': snippet,
                'matched_at': msg.created_at,
            })

    return Response({'items': hits})


def _make_snippet(content: str, keyword: str, padding: int = 24) -> str:
    """从命中长文本中截取关键词附近的小段（高亮交给前端）。

    Args:
        content (str): 完整正文。
        keyword (str): 搜索关键词。
        padding (int): 关键词前后保留多少字符。

    Returns:
        str: 截取片段，超出原文长度时直接返回完整内容。
    """
    if not content:
        return ''
    lower_content = content.lower()
    idx = lower_content.find(keyword.lower())
    if idx == -1:
        return content[: padding * 2] + ('…' if len(content) > padding * 2 else '')

    start = max(0, idx - padding)
    end = min(len(content), idx + len(keyword) + padding)
    snippet = content[start:end]
    if start > 0:
        snippet = '…' + snippet
    if end < len(content):
        snippet = snippet + '…'
    return snippet


@api_view(['POST'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def cancel_message(request: Request, public_id) -> Response:
    """取消正在生成的消息。

    实现方式：标记消息为 CANCELLED 并向 Celery 发取消信号。
    前端订阅端会收到广播的 done 事件后停止流式 UI。

    Args:
        request (Request): DRF 请求。
        public_id: 消息对外 UUID。
    """
    try:
        message = AiMessage.objects.select_related('conversation').get(
            public_id=public_id,
            conversation__user=request.user,
        )
    except AiMessage.DoesNotExist:
        return Response({'detail': '消息不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)

    if message.status not in (MessageStatus.PENDING, MessageStatus.STREAMING):
        return Response({'detail': '当前消息状态不可取消'}, status=status.HTTP_400_BAD_REQUEST)

    if message.task_id:
        from backend_master.celery import app as celery_app
        try:
            celery_app.control.revoke(message.task_id, terminate=True, signal='SIGTERM')
        except Exception as exc:
            logger.warning(
                '[ai_chat_view][cancel_message] revoke 失败但仍标记取消: msg=%s err=%s',
                message.id,
                str(exc),
            )

    AiMessage.objects.filter(pk=message.pk).update(status=MessageStatus.CANCELLED)

    # 向订阅端广播 done 让 SSE 流自然收尾（Pub/Sub 频道仍按内部整数 pk 寻址）
    from apps.ai.utils.redis_channel import EVENT_DONE, get_redis_client, publish_event
    try:
        publish_event(get_redis_client(), message.id, EVENT_DONE, {'cancelled': True})
    except Exception as exc:
        logger.warning('[ai_chat_view][cancel_message] 广播 done 失败: %s', str(exc))

    return Response({'success': True})
