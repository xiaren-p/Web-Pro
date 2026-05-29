"""自定义 Bearer Token 认证（基于 :class:`AuthToken` 模型）。"""
from typing import Optional, Tuple

from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from api_v1.models import AuthToken


class BearerTokenAuthentication(BaseAuthentication):
    """读取 ``Authorization: Bearer <token>`` 头，校验访问令牌有效性。"""

    keyword = b"Bearer"

    def authenticate(self, request) -> Optional[Tuple[User, AuthToken]]:
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower():
            return None
        if len(auth) == 1:
            raise AuthenticationFailed("无效的认证头")
        if len(auth) > 2:
            raise AuthenticationFailed("无效的认证头")
        token = auth[1].decode()
        try:
            at = AuthToken.objects.select_related("user").get(access_token=token, revoked=False)
        except AuthToken.DoesNotExist:
            # 返回 None 而非抛出异常，使认证链继续尝试下一个认证器（如 OAuth2Authentication）
            return None
        if not at.is_access_valid():
            raise AuthenticationFailed("令牌已过期")
        return at.user, at
