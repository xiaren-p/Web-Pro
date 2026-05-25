"""任务 API 视图（task_view）。

职责：HTTP 请求解析、参数验证、调用 TaskService、包装 HTTP 响应。
严禁在此处编写业务计算逻辑，所有业务操作均委托给 WorkflowService。

鉴权模式：
- 普通用户（BearerTokenAuthentication）：基于 request.user 过滤与操作。
- Client Credentials 应用（OAuth2Authentication）：通过应用注册用户代理执行，
  任务执行记录归属于注册该应用的用户（app.user），而非匿名身份。
"""

import logging
from typing import Optional

from django.contrib.auth.models import User
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.models import get_access_token_model
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth.bearer_token_auth import BearerTokenAuthentication
from api_v2.models.workflow_execution import WorkflowExecution
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.serializers.task_serializer import (
    WorkflowExecutionSerializer,
    WorkflowStartSerializer,
)
from api_v2.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

_AccessToken = get_access_token_model()

# 统一鉴权配置：普通用户 Bearer Token + OAuth2 Client Credentials 双路鉴权
_V2_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_V2_PERM = [IsV2Accessible]


def _resolve_actor_user(request: Request) -> Optional[User]:
    """
    从 request 中解析实际操作用户。

    普通用户请求直接返回 request.user；Client Credentials 请求通过
    Application.user 获取注册者作为代理用户，保证 WorkflowExecution.user
    始终指向一个真实的 Django User。

    Args:
        request (Request): DRF 请求对象。

    Returns:
        Optional[User]: 解析出的 Django User；无法解析时返回 None
            （正常情况下 IsV2Accessible 已前置拦截，此处不应为 None）。
    """
    if request.user and request.user.is_authenticated:
        return request.user

    token = request.auth
    if (
        isinstance(token, _AccessToken)
        and token.application
        and token.application.user
    ):
        return token.application.user

    return None


@api_view(['POST'])
@authentication_classes(_V2_AUTH)
@permission_classes(_V2_PERM)
def start_workflow(request: Request) -> Response:
    """启动异步任务。

    同一类型任务同时仅允许一个执行，重复提交返回 409 Conflict。
    Client Credentials 应用调用时，任务归属于应用注册用户。

    POST /api/v2/tasks/
    {
        "workflow_type": "listing_image_upload",
        "params": {"listing_id": 1, "image_ids": [10, 11, 12]}
    }
    """
    actor_user = _resolve_actor_user(request)
    if actor_user is None:
        logger.error("[start_workflow] 无法解析操作用户，请求被拒绝")
        return Response({'detail': '无法解析操作用户'}, status=status.HTTP_403_FORBIDDEN)

    serializer = WorkflowStartSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    workflow_type: str = serializer.validated_data['workflow_type']
    params: dict = serializer.validated_data.get('params', {})

    try:
        execution = WorkflowService.create_and_enqueue(
            user=actor_user,
            workflow_type=workflow_type,
            params=params,
        )
        return Response(
            WorkflowExecutionSerializer(execution).data,
            status=status.HTTP_201_CREATED,
        )

    except ValueError as exc:
        logger.warning("[start_workflow] 冲突或参数错误: %s", exc)
        return Response(
            {'detail': str(exc)},
            status=status.HTTP_409_CONFLICT,
        )

    except Exception as exc:
        logger.error("[start_workflow] 任务创建失败: %s", exc, exc_info=True)
        return Response(
            {'detail': '任务创建失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@authentication_classes(_V2_AUTH)
@permission_classes(_V2_PERM)
def get_workflow_status(request: Request, execution_id: int) -> Response:
    """查询任务执行状态（同步 Celery 实时状态后返回）。

    Client Credentials 应用只能查询归属于其注册用户的执行记录。

    GET /api/v2/tasks/{execution_id}/
    """
    actor_user = _resolve_actor_user(request)
    if actor_user is None:
        return Response({'detail': '无法解析操作用户'}, status=status.HTTP_403_FORBIDDEN)

    try:
        execution = WorkflowExecution.objects.get(
            id=execution_id,
            user=actor_user,
        )
    except WorkflowExecution.DoesNotExist:
        return Response(
            {'detail': '执行记录不存在'},
            status=status.HTTP_404_NOT_FOUND,
        )

    execution = WorkflowService.sync_status(execution)
    return Response(WorkflowExecutionSerializer(execution).data)


@api_view(['POST'])
@authentication_classes(_V2_AUTH)
@permission_classes(_V2_PERM)
def cancel_workflow(request: Request, execution_id: int) -> Response:
    """取消正在执行的任务。

    Client Credentials 应用只能取消归属于其注册用户的执行记录。

    POST /api/v2/tasks/{execution_id}/cancel/
    """
    actor_user = _resolve_actor_user(request)
    if actor_user is None:
        return Response({'detail': '无法解析操作用户'}, status=status.HTTP_403_FORBIDDEN)

    try:
        execution = WorkflowService.cancel(
            execution_id=execution_id,
            user=actor_user,
        )
        return Response(WorkflowExecutionSerializer(execution).data)

    except WorkflowExecution.DoesNotExist:
        return Response(
            {'detail': '执行记录不存在'},
            status=status.HTTP_404_NOT_FOUND,
        )

    except ValueError as exc:
        return Response(
            {'detail': str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as exc:
        logger.error("[cancel_workflow] 取消失败: %s", exc, exc_info=True)
        return Response(
            {'detail': '取消操作失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
