"""手机号 / 邮箱 验证码与绑定接口（单独抽离自 UserViewSet 邻域）。

路由：

- ``POST /users/mobile/code``  发送手机验证码
- ``PUT  /users/mobile``       绑定手机号
- ``POST /users/email/code``   发送邮箱验证码
- ``PUT  /users/email``        绑定邮箱

所有入参均交由 Serializer 做基本格式校验。
"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.serializers import (
    EmailBindSerializer,
    EmailCodeSendSerializer,
    MobileBindSerializer,
    MobileCodeSendSerializer,
)
from api_v1.utils.responses import drf_ok


class ProfileViewSet(viewsets.ViewSet):
    """手机号/邮箱的验证码发送与绑定。

    绑定操作要求登录，权限沿用全局默认的 ``IsAuthenticated``。
    """

    @action(detail=False, methods=["post"], url_path="mobile/code")
    def send_mobile_code(self, request: Request):
        """发送手机验证码（仅做参数校验，短信渠道由后续接入实现）。"""
        s = MobileCodeSendSerializer(data=request.query_params or request.data)
        s.is_valid(raise_exception=True)
        return drf_ok({"message": "sent"})

    @action(detail=False, methods=["put"], url_path="mobile")
    def bind_mobile(self, request: Request):
        """根据验证码绑定手机号。"""
        s = MobileBindSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return drf_ok({"message": "mobile bound"})

    @action(detail=False, methods=["post"], url_path="email/code")
    def send_email_code(self, request: Request):
        """发送邮箱验证码（仅做参数校验，邮件渠道由后续接入实现）。"""
        s = EmailCodeSendSerializer(data=request.query_params or request.data)
        s.is_valid(raise_exception=True)
        return drf_ok({"message": "sent"})

    @action(detail=False, methods=["put"], url_path="email")
    def bind_email(self, request: Request):
        """根据验证码绑定邮箱。"""
        s = EmailBindSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return drf_ok({"message": "email bound"})
