"""AI 对话视图（ai_chat_view）：非流式接口集合。

职责：
    - POST /chat/                       提交问题，入队 Celery 任务，返回消息 ID（不等流）
    - GET  /conversations/              当前用户会话列表
    - GET  /conversations/<id>/messages/ 拉取某会话的全部消息（用于刷新页面回放）
    - POST /messages/<id>/cancel/        取消正在生成的消息
SSE 流式订阅请见 ``ai_stream_view`` 模块。
"""

import logging

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth.bearer_token_auth import BearerTokenAuthentication
from api_v2.models.ai_conversation import AiConversation
from api_v2.models.ai_message import AiMessage, MessageStatus
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.serializers.ai_chat_serializer import (
    AiChatRequestSerializer,
    AiConversationSerializer,
    AiMessageSerializer,
)
from api_v2.services.ai.ai_chat_service import AiChatService

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
    """返回当前用户的会话列表（按最后活跃时间倒序，默认前 50 条）。"""
    queryset = AiConversation.objects.filter(user=request.user)[:50]
    data = AiConversationSerializer(queryset, many=True).data
    return Response({'items': data})


@api_view(['GET'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def list_messages(request: Request, conversation_id: int) -> Response:
    """返回某会话下的全部消息正文（用于刷新页面后的历史回放）。"""
    try:
        AiConversation.objects.get(id=conversation_id, user=request.user)
    except AiConversation.DoesNotExist:
        return Response({'detail': '会话不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)

    messages = AiMessage.objects.filter(conversation_id=conversation_id).order_by('created_at')
    data = AiMessageSerializer(messages, many=True).data
    return Response({'items': data})


@api_view(['DELETE'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def delete_conversation(request: Request, conversation_id: int) -> Response:
    """删除会话及其所有消息（级联）。"""
    deleted, _ = AiConversation.objects.filter(id=conversation_id, user=request.user).delete()
    if not deleted:
        return Response({'detail': '会话不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'success': True})


@api_view(['POST'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def cancel_message(request: Request, message_id: int) -> Response:
    """取消正在生成的消息。

    实现方式：标记消息为 CANCELLED 并向 Celery 发取消信号。
    前端订阅端会收到广播的 done 事件后停止流式 UI。
    """
    try:
        message = AiMessage.objects.select_related('conversation').get(
            id=message_id,
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
                message_id,
                str(exc),
            )

    AiMessage.objects.filter(id=message_id).update(status=MessageStatus.CANCELLED)

    # 向订阅端广播 done 让 SSE 流自然收尾
    from api_v2.utils.ai_redis_channel import EVENT_DONE, get_redis_client, publish_event
    try:
        publish_event(get_redis_client(), message_id, EVENT_DONE, {'cancelled': True})
    except Exception as exc:
        logger.warning('[ai_chat_view][cancel_message] 广播 done 失败: %s', str(exc))

    return Response({'success': True})
