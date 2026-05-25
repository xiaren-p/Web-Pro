"""工作流模块权限类（workflow_permission）。"""

import logging
from typing import Any

from oauth2_provider.models import get_access_token_model
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

logger = logging.getLogger(__name__)

_V2_REQUIRED_SCOPE = 'api_v2'


class IsV2Accessible(BasePermission):
    """
    api_v2 接口统一访问权限类。

    支持两类合法调用方：

    1. 通过 BearerTokenAuthentication 鉴权的普通用户（request.user 已认证）。
    2. 通过 OAuth2 Client Credentials 授权的外部应用（request.auth 为携带
       api_v2 scope 的 AccessToken）。

    其他调用方（未携带凭证、凭证无效、scope 不足）一律返回 403 Forbidden。
    """

    message = (
        '无访问权限：需要有效的用户凭证或携带 api_v2 scope 的 Client Credentials Token。'
    )

    def has_permission(self, request: Request, view: Any) -> bool:
        """
        校验请求是否有权限访问 api_v2 接口。

        Args:
            request (Request): DRF 请求对象。
            view (Any): 当前视图对象。

        Returns:
            bool: 有权限返回 True，无权限返回 False。
        """
        # 路径 1：普通用户（BearerToken / Session）
        if request.user and request.user.is_authenticated:
            return True

        # 路径 2： OAuth2 Client Credentials（含 api_v2 scope）
        AccessToken = get_access_token_model()
        token = request.auth
        if isinstance(token, AccessToken):
            valid = token.is_valid([_V2_REQUIRED_SCOPE])
            if not valid:
                logger.warning(
                    "[IsV2Accessible] Token scope 不足或已过期: token_pk=%s",
                    getattr(token, 'pk', '?'),
                )
            return valid

        return False
