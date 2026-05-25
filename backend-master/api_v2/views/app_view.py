"""开发者应用管理视图（app_view）。

职责：为前端「开发者设置」页面提供 Client Credentials 应用的 CRUD 与密钥轮换接口。

安全约束：
- 仅允许已认证的普通用户（BearerToken）操作，Client Credentials Token 本身不得管理应用。
- 每个用户只能查看、管理自己注册的应用（user 字段强制过滤）。
- 删除应用时级联撤销全部关联 AccessToken。
- 轮换密钥时同步撤销当前所有有效 AccessToken，强制客户端重新获取。
"""

import logging
import secrets

from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_application_model
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth.bearer_token_auth import BearerTokenAuthentication
from api_v2.serializers.app_serializer import (
    AppCreateSerializer,
    AppCreatedSerializer,
    AppListItemSerializer,
    SecretRotatedSerializer,
)

logger = logging.getLogger(__name__)

Application = get_application_model()
AccessToken = get_access_token_model()

# 开发者管理接口仅对人类用户开放，不接受机器令牌
_DEV_AUTH = [BearerTokenAuthentication]
_DEV_PERM = [IsAuthenticated]


@api_view(['GET'])
@authentication_classes(_DEV_AUTH)
@permission_classes(_DEV_PERM)
def list_apps(request: Request) -> Response:
    """
    列出当前用户的所有 Client Credentials 应用。

    GET /api/v2/developer/apps/

    Returns:
        200: { results: AppListItem[] }
    """
    apps = Application.objects.filter(
        user=request.user,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    ).order_by('-created')

    return Response({'results': AppListItemSerializer(apps, many=True).data})


@api_view(['POST'])
@authentication_classes(_DEV_AUTH)
@permission_classes(_DEV_PERM)
def create_app(request: Request) -> Response:
    """
    创建新的 Client Credentials 应用。

    POST /api/v2/developer/apps/
    { "name": "我的自动化脚本" }

    Returns:
        201: AppCreated（含 client_secret，仅此一次）
        400: 参数校验失败
    """
    serializer = AppCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    name: str = serializer.validated_data['name']

    application = Application.objects.create(
        user=request.user,
        name=name,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        redirect_uris='',
        skip_authorization=True,
    )

    logger.info(
        "[create_app] 用户创建 Client Credentials 应用: user=%s name=%s client_id=%s",
        request.user.username,
        name,
        application.client_id,
    )

    return Response(AppCreatedSerializer(application).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@authentication_classes(_DEV_AUTH)
@permission_classes(_DEV_PERM)
def delete_app(request: Request, app_id: int) -> Response:
    """
    删除指定应用，级联删除所有关联 AccessToken。

    DELETE /api/v2/developer/apps/{app_id}/

    Returns:
        204: 删除成功
        404: 应用不存在
    """
    try:
        application = Application.objects.get(
            id=app_id,
            user=request.user,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        )
    except Application.DoesNotExist:
        return Response({'detail': '应用不存在'}, status=status.HTTP_404_NOT_FOUND)

    client_id = application.client_id
    application.delete()  # DOT 级联删除关联 AccessToken

    logger.info(
        "[delete_app] 用户删除应用: user=%s app_id=%s client_id=%s",
        request.user.username,
        app_id,
        client_id,
    )

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@authentication_classes(_DEV_AUTH)
@permission_classes(_DEV_PERM)
def rotate_secret(request: Request, app_id: int) -> Response:
    """
    轮换应用 Client Secret，同时撤销当前所有有效 AccessToken。

    POST /api/v2/developer/apps/{app_id}/rotate-secret/

    安全说明：
    - 生成 48 字节（384 bit）的密码学随机 Secret，Base64-URL 编码为 64 字符。
    - 轮换后立即撤销该应用所有现存 AccessToken，强制重新认证，
      防止旧 Secret 泄露后已颁发的 Token 仍被滥用。
    - 新 Secret 仅在此响应中返回一次，请前端强制引导用户保存。

    Returns:
        200: { client_secret, rotated_at }
        404: 应用不存在
    """
    try:
        application = Application.objects.get(
            id=app_id,
            user=request.user,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        )
    except Application.DoesNotExist:
        return Response({'detail': '应用不存在'}, status=status.HTTP_404_NOT_FOUND)

    # 撤销所有当前有效的 AccessToken，防止旧 Secret 泄露后仍被使用
    revoked_count, _ = AccessToken.objects.filter(application=application).delete()

    # 生成高强度随机 Secret（48 字节 → 64 字符 Base64-URL）
    new_secret = secrets.token_urlsafe(48)
    application.client_secret = new_secret
    application.save(update_fields=['client_secret'])

    rotated_at = timezone.now()

    logger.info(
        "[rotate_secret] 密钥轮换成功: user=%s app_id=%s revoked_tokens=%s",
        request.user.username,
        app_id,
        revoked_count,
    )

    serializer = SecretRotatedSerializer({
        'client_secret': new_secret,
        'rotated_at': rotated_at,
    })
    return Response(serializer.data)
