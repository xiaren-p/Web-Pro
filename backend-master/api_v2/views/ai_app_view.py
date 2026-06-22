"""AI Dify 应用列表视图（ai_app_view）。

仅暴露给前端\"应用切换器\"使用，返回当前激活的全部 Dify 应用元数据
（不含 API Key 等敏感字段）。
"""

import logging

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth.bearer_token_auth import BearerTokenAuthentication
from api_v2.models.dify_app import DifyApp
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.serializers.ai_chat_serializer import DifyAppSerializer

logger = logging.getLogger(__name__)


_AUTH = [BearerTokenAuthentication, OAuth2Authentication]
_PERM = [IsV2Accessible]


@api_view(['GET'])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def list_apps(request: Request) -> Response:
    """返回当前激活的全部 Dify 应用，按 ``sort_order`` 升序。

    用于前端 ChatPanel 输入区的\"应用切换器 chip\"渲染下拉列表。
    不返回 ``api_base`` / ``api_key_encrypted`` 等敏感字段。

    Returns:
        Response: ``{"items": [{id, code, name, description, icon, mode, is_default, sort_order}, ...]}``
    """
    queryset = DifyApp.objects.filter(is_active=True).order_by('sort_order', 'id')
    data = DifyAppSerializer(queryset, many=True).data
    return Response({'items': data})
