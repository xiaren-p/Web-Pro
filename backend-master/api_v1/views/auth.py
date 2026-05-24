"""身份认证视图（登录/登出/刷新 token 等）。

模块说明：提供用户登录、刷新 token、登出与图形验证码接口。
"""

import logging

from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from django.conf import settings
import uuid
from api_v1.models import AuthToken
from api_v1.utils.responses import drf_ok, drf_error
# note: write_log calls removed per request; use centralized logging if needed
from api_v1.utils.captcha import generate_captcha, validate_captcha
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

class AuthViewSet(viewsets.ViewSet):
    """身份认证相关接口（登录/登出/刷新 token 等）"""
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        action = getattr(self, 'action', None)
        # 允许匿名访问的动作：登录、图形验证码、刷新 token（刷新 token 使用 refreshToken 字段）
        if action in ("login", "captcha", "refresh_token"):
            return [AllowAny()]
        return super().get_permissions()

    def get_authenticators(self):
        """login / captcha / refresh_token 动作排除 SessionAuthentication。

        ssoSession 会在浏览器留下持久 Session Cookie，用户退出后该 Cookie 仍在。
        若登录请求被 SessionAuthentication 可见，就会强制校验 CSRF token，
        而前端 login 请求未携带 CSRF token → CSRF Failed。
        """
        from rest_framework.authentication import SessionAuthentication
        base = super().get_authenticators()
        action = getattr(self, 'action', None)
        if action in ('login', 'captcha', 'refresh_token'):
            return [a for a in base if not isinstance(a, SessionAuthentication)]
        return base

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):  # pragma: no cover
        t0 = timezone.now()
        username = (request.data or {}).get('username')
        password = (request.data or {}).get('password')
        # 验证图形验证码（前端应同时提交 captchaKey 与 captchaCode）
        captcha_key = (request.data or {}).get('captchaKey')
        captcha_code = (request.data or {}).get('captchaCode')
        if not captcha_key or not captcha_code:
            return drf_error("验证码缺失", status=400)
        try:
            # 首先尝试使用共享 cache 验证
            if not validate_captcha(captcha_key, captcha_code):
                # 若 cache 验证失败，尝试回退到 session（若客户端与服务在同一浏览器，会携带 sessionid）
                # 开发/测试用途：允许通过配置的万能验证码跳过校验（需在 .env 中设置 ALLOW_CAPTCHA_BYPASS=true 与 CAPTCHA_MASTER_CODE）
                try:
                    # 检查是否启用了万能验证码并匹配
                    bypass_allowed = getattr(settings, 'ALLOW_CAPTCHA_BYPASS', False)
                    master_code = getattr(settings, 'CAPTCHA_MASTER_CODE', None)
                    if bypass_allowed and master_code and str(captcha_code) == str(master_code):
                        # 万能验证码命中，直接通过
                        pass
                    else:
                        sess_val = request.session.get(f"captcha:{captcha_key}")
                        if sess_val and isinstance(sess_val, str) and sess_val.strip():
                            # reuse captcha normalization from utils.captcha
                            try:
                                import unicodedata
                            except Exception:
                                unicodedata = None

                            def _norm(s: str) -> str:
                                if s is None:
                                    return ''
                                s2 = str(s)
                                if unicodedata:
                                    try:
                                        s2 = unicodedata.normalize('NFKC', s2)
                                    except Exception:
                                        pass
                                return s2.strip().lower()

                            if _norm(sess_val) == _norm(captcha_code):
                                # session 验证通过，删除 session 存储并继续
                                try:
                                    del request.session[f"captcha:{captcha_key}"]
                                except Exception:
                                    pass
                            else:
                                return drf_error("验证码错误", status=400)
                        else:
                            return drf_error("验证码错误", status=400)
                except Exception:
                    return drf_error("验证码校验失败", status=400)
        except Exception:
            return drf_error("验证码校验失败", status=400)
        if not username or not password:
            return drf_error("用户名或密码不能为空", status=400)

        # 校验账号密码
        user = authenticate(username=username, password=password)
        if not user:
            return drf_error("用户名或密码错误", status=401)

        # 生成 access / refresh token
        access_ttl = getattr(settings, 'ACCESS_TOKEN_EXPIRE_SECONDS', 86400)
        refresh_ttl = getattr(settings, 'REFRESH_TOKEN_EXPIRE_SECONDS', 7 * 86400)
        at = AuthToken.objects.create(
            user=user,
            access_token=uuid.uuid4().hex,
            refresh_token=uuid.uuid4().hex,
            access_expires_at=timezone.now() + timezone.timedelta(seconds=access_ttl),
            refresh_expires_at=timezone.now() + timezone.timedelta(seconds=refresh_ttl),
        )

        resp = {
            "accessToken": at.access_token,
            "refreshToken": at.refresh_token,
            "tokenType": "Bearer",
            "expiresIn": access_ttl,
        }
        return drf_ok(resp)

    @csrf_exempt
    @action(detail=False, methods=["post"], url_path="refresh-token")
    def refresh_token(self, request):  # pragma: no cover
        token = request.query_params.get('refreshToken') or (request.data or {}).get('refreshToken')
        if not token:
            return drf_error("缺少 refreshToken", status=400)
        try:
            obj = AuthToken.objects.get(refresh_token=token, revoked=False)
        except AuthToken.DoesNotExist:
            return drf_error("刷新令牌无效", status=401)
        if not obj.is_refresh_valid():
            return drf_error("刷新令牌已过期", status=401)
        # 生成新的 access token（不旋转 refresh）
        access_ttl = getattr(settings, 'ACCESS_TOKEN_EXPIRE_SECONDS', 86400)
        obj.access_token = uuid.uuid4().hex
        obj.access_expires_at = timezone.now() + timezone.timedelta(seconds=access_ttl)
        obj.save(update_fields=["access_token", "access_expires_at", "updated_at"])
        # refresh token logging removed
        return drf_ok({
            "accessToken": obj.access_token,
            "tokenType": "Bearer",
            "expiresIn": access_ttl,
        })

    @action(detail=False, methods=["delete", "get", "post"], url_path="logout")
    def logout(self, request):  # pragma: no cover
        # 提前缓存用户引用：django_logout() 会清空 request.user，之后无法取到
        logout_user = request.user if request.user and request.user.is_authenticated else None

        # 撤销 JWT access token
        try:
            from rest_framework.authentication import get_authorization_header
            parts = get_authorization_header(request).split()
            if parts and len(parts) == 2 and parts[0].lower() == b"bearer":
                tok = parts[1].decode()
                AuthToken.objects.filter(access_token=tok, revoked=False).update(revoked=True)
        except Exception:
            pass
        # 同时清除 Django Session，防止 ssoSession 建立的 Session Cookie
        # 退出后残留并导致下次登录被 SessionAuthentication 强制校验 CSRF。
        try:
            django_logout(request)
        except Exception:
            pass

        # OIDC Back-Channel Logout：向 NC 推送注销令牌，实现无感同步退出
        if logout_user is not None:
            from api_v1.services.oidc.oidc_logout_service import push_backchannel_logout
            push_backchannel_logout(logout_user)

        return drf_ok(status=204)

    @action(detail=False, methods=["get"], url_path="captcha")
    def captcha(self, request):  # pragma: no cover
        # 生成图形验证码（若 PIL 不可用，回退为透明 1x1 PNG）
        try:
            key, img_b64, _text = generate_captcha()
        except Exception as e:
            try:
                import traceback
                traceback.print_exc()
            except Exception:
                pass
            return drf_error("生成验证码失败", status=500)
        # 保存到 session 以兼容多进程部署下的本地缓存失效问题（如果 CACHES 未配置为共享存储）
        try:
            # session 会被序列化到后端存储（cookie/db/redis），客户端会在后续请求中携带
            request.session[f"captcha:{key}"] = _text
        except Exception:
            pass
        return drf_ok({"img": img_b64, "uuid": key})

    @action(detail=False, methods=["post"], url_path="sso-session")
    def sso_session(self, request):
        """用已有 Bearer JWT 换取 Django Session Cookie，以便完成 OIDC 授权码流程。

        前端在打开 Nextcloud SSO 链接前调用此接口（携带 Authorization: Bearer <token>），
        后端验证通过后建立 Django Session，浏览器后续请求 /o/authorize/ 时即被识别为已登录。

        Returns:
            200 {"detail": "session 已建立"} + Set-Cookie: sessionid=...
            401 若 token 无效或已过期。
        """
        user = request.user
        if not user or not user.is_authenticated:
            return drf_error("认证失败，请先登录系统", status=401)

        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        logger.info(
            "[AuthViewSet][sso_session] 用户 %s 换取 Django Session 成功", user.username,
        )
        return drf_ok({"detail": "session 已建立，可继续 OIDC 授权"})
