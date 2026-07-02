"""AI 对话分组视图（ai_group_view）：分组 CRUD + 移动会话。"""

import logging

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from apps.system.auth.bearer_token_auth import BearerTokenAuthentication
from apps.ai.models.conversation_group import AiConversationGroup
from apps.system.permissions.v2_access import IsV2Accessible
from apps.ai.serializers.chat_serializer import AiConversationGroupSerializer
from apps.ai.services.group_service import AiGroupService

logger = logging.getLogger(__name__)


_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]


@api_view(['GET'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def list_groups(request: Request) -> Response:
    """返回当前用户的全部分组（按 order 升序）。"""
    groups = AiGroupService().list_groups(request.user)
    data = AiConversationGroupSerializer(groups, many=True).data
    return Response({'items': data})


@api_view(['POST'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def create_group(request: Request) -> Response:
    """新建一个分组。Body: {"name": "..."}"""
    name = (request.data or {}).get('name', '') if request.data else ''
    try:
        group = AiGroupService().create_group(request.user, name)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(AiConversationGroupSerializer(group).data, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def rename_group(request: Request, public_id) -> Response:
    """重命名分组。Body: {"name": "..."}"""
    name = (request.data or {}).get('name', '') if request.data else ''
    try:
        group = AiGroupService().rename_group(request.user, public_id, name)
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except AiConversationGroup.DoesNotExist:
        return Response({'detail': '分组不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)

    return Response(AiConversationGroupSerializer(group).data)


@api_view(['DELETE'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def delete_group(request: Request, public_id) -> Response:
    """删除分组（关联会话变为未分组）。"""
    try:
        AiGroupService().delete_group(request.user, public_id)
    except AiConversationGroup.DoesNotExist:
        return Response({'detail': '分组不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'success': True})


@api_view(['POST'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def reorder_groups(request: Request) -> Response:
    """按前端提交的顺序更新分组排序。Body: {"ordered_ids": ["uuid1", "uuid2", ...]}"""
    ordered_ids = (request.data or {}).get('ordered_ids') or []
    if not isinstance(ordered_ids, list):
        return Response({'detail': 'ordered_ids 必须是 UUID 数组'}, status=status.HTTP_400_BAD_REQUEST)

    AiGroupService().reorder_groups(request.user, ordered_ids)
    return Response({'success': True})


@api_view(['POST'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def move_conversation_to_group(request: Request, public_id) -> Response:
    """把会话移到指定分组。

    Args:
        public_id: 会话 public_id（路径参数）。
        Body: {"group_id": "uuid" | null}  group_id 为 null 表示移出所有分组。
    """
    body = request.data or {}
    target_group_id = body.get('group_id')   # 允许 None

    from apps.ai.models.conversation import AiConversation
    try:
        AiGroupService().move_conversation(
            user=request.user,
            conversation_public_id=public_id,
            group_public_id=target_group_id,
        )
    except AiConversation.DoesNotExist:
        return Response({'detail': '会话不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)
    except AiConversationGroup.DoesNotExist:
        return Response({'detail': '目标分组不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'success': True})
