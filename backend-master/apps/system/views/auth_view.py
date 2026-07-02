"""身份认证视图（登录/登出/刷新 token 等）。

模块说明：提供用户登录、刷新 token、登出与图形验证码接口。
全部业务逻辑委托至 :mod:`apps.system.services.auth_service`。
"""

import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt

from apps.common.utils.responses import drf_ok, drf_error
from apps.system.services.auth_service import (
    login as auth_login,
    refresh_token as auth_refresh,
    logout as auth_logout,
    generate_captcha_image,
    establish_sso_session,
)

logger = logging.getLogger(__name__)


class AuthViewSet(viewsets.ViewSet):
    """身份认证相关接口（登录/登出/刷新 token 等）。"""

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """返回当前 action 所需的权限类列表。"""
        action = getattr(self, 'action', None)
        if action in ("login", "captcha", "refresh_token"):
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):  # pragma: no cover
        """用户登录：验证码校验 → 账号密码认证 → 签发 Token。"""
        payload = request.data or {}
        result = auth_login(
            payload.get("username"),
            payload.get("password"),
            payload.get("captchaKey"),
            payload.get("captchaCode"),
            request,
        )
        if isinstance(result, tuple):
            return drf_error(result[0], status=result[1])
        return drf_ok(result)

    @csrf_exempt
    @action(detail=False, methods=["post"], url_path="refresh-token")
    def refresh_token(self, request):  # pragma: no cover
        """刷新访问令牌。"""
        token = request.query_params.get('refreshToken') or (request.data or {}).get('refreshToken')
        result = auth_refresh(token)
        if isinstance(result, tuple):
            return drf_error(result[0], status=result[1])
        return drf_ok(result)

    @action(detail=False, methods=["delete", "get", "post"], url_path="logout")
    def logout(self, request):  # pragma: no cover
        """用户登出。"""
        auth_logout(request)
        return drf_ok(status=204)

    @action(detail=False, methods=["get"], url_path="captcha")
    def captcha(self, request):  # pragma: no cover
        """生成验证码。"""
        result = generate_captcha_image(request)
        if isinstance(result, tuple):
            return drf_error(result[0], status=result[1])
        return drf_ok(result)

    @action(detail=False, methods=["post"], url_path="sso-session")
    def sso_session(self, request):
        """用已有 Bearer Token 换取 Django Session Cookie。

        前端在打开 Nextcloud SSO 链接前调用此接口（携带 Authorization: Bearer <token>），
        后端验证通过后建立 Django Session，浏览器后续请求 /o/authorize/ 时即被识别为已登录。

        Returns:
            200 {"detail": "session 已建立"} + Set-Cookie: sessionid=...
            401 若 token 无效或已过期。
        """
        msg, status = establish_sso_session(request)
        if status != 200:
            return drf_error(msg, status=status)
        return drf_ok({"detail": msg})
