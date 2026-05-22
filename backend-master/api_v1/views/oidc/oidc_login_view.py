"""OIDC SSO 登录页视图：为 /accounts/login/ 提供标准 Django Session 登录。

oauth2_provider 在用户未登录时重定向到 settings.LOGIN_URL（默认 /accounts/login/），
此视图接管该路由，完成 username/password → Django Session 的认证，
认证后跳回 ?next= 参数（即 /o/authorize/?...），继续授权码流程。
"""
import logging

from django.contrib.auth import authenticate, login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
def oidc_login_view(request: HttpRequest) -> HttpResponse:
    """OIDC 授权前置登录页。

    GET  → 渲染登录表单。
    POST → 验证用户名/密码，成功后建立 Django Session 并跳回 next。

    Args:
        request (HttpRequest): Django 请求对象。

    Returns:
        HttpResponse: GET 返回 HTML 页面；POST 成功返回重定向；失败重渲染表单。
    """
    # 已登录用户直接跳走
    if request.user.is_authenticated:
        next_url = request.GET.get("next") or request.POST.get("next") or "/"
        return redirect(next_url)

    error: str = ""
    username: str = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        next_url = request.POST.get("next") or request.GET.get("next") or "/"

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info(
                "[oidc_login_view] 用户 %s 通过 OIDC 登录页完成认证，重定向至 next=%s",
                user.username,
                next_url,
            )
            return redirect(next_url)

        error = "用户名或密码不正确，请重试。"
        logger.warning(
            "[oidc_login_view] 登录失败，username=%s remote_addr=%s",
            username,
            request.META.get("REMOTE_ADDR"),
        )

    return render(
        request,
        "oidc_login.html",
        {
            "error": error,
            "next": request.GET.get("next", ""),
            "username": username,
        },
    )
