"""身份认证视图（登录/登出/刷新 token 等）。

模块说明：提供用户登录、刷新 token、登出与图形验证码接口。
"""

import logging

from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.middleware.csrf import rotate_token
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


def _normalize_captcha(text: str) -> str:
    """对验证码文本做 NFKC 归一化，用于大小写不敏感 + 全半角兼容比对。

    Args:
        text: 原始验证码文本

    Returns:
        归一化后的小写 stripped 字符串
    """
    if not text:
        return ""
    try:
        import unicodedata
        return unicodedata.normalize("NFKC", str(text)).strip().lower()
    except Exception:
        return str(text).strip().lower()


def _validate_captcha_request(captcha_key: str, captcha_code: str, request) -> str | None:
    """验证图形验证码。返回 None 表示通过，否则返回错误信息字符串。

    验证顺序：
    1. 共享 cache 验证（validate_captcha）
    2. 万能验证码（ALLOW_CAPTCHA_BYPASS + CAPTCHA_MASTER_CODE）
    3. Session 回退验证

    Args:
        captcha_key: 验证码 key
        captcha_code: 用户输入的验证码
        request: DRF request 对象

    Returns:
        None 表示验证通过；非空字符串为错误信息。
    """
    # 第 1 层：共享 cache 验证
    if validate_captcha(captcha_key, captcha_code):
        return None

    # 第 2 层：万能验证码（开发/测试用途）
    bypass_allowed = getattr(settings, "ALLOW_CAPTCHA_BYPASS", False)
    master_code = getattr(settings, "CAPTCHA_MASTER_CODE", None)
    if bypass_allowed and master_code and str(captcha_code) == str(master_code):
        return None

    # 第 3 层：Session 回退验证
    sess_val = request.session.get(f"captcha:{captcha_key}")
    if not sess_val or not isinstance(sess_val, str) or not sess_val.strip():
        return "验证码错误"

    if _normalize_captcha(sess_val) == _normalize_captcha(captcha_code):
        try:
            del request.session[f"captcha:{captcha_key}"]
        except Exception:
            pass
        return None

    return "验证码错误"


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
        """用户登录：验证码校验 → 账号密码认证 → 签发 Token。"""
        payload = request.data or {}
        username = payload.get("username")
        password = payload.get("password")
        captcha_key = payload.get("captchaKey")
        captcha_code = payload.get("captchaCode")

        # 1. 参数校验
        if not captcha_key or not captcha_code:
            return drf_error("验证码缺失", status=400)
        if not username or not password:
            return drf_error("用户名或密码不能为空", status=400)

        # 2. 验证码校验
        captcha_err = _validate_captcha_request(captcha_key, captcha_code, request)
        if captcha_err:
            return drf_error(captcha_err, status=400)

        # 3. 账号密码认证
        user = authenticate(username=username, password=password)
        if not user:
            return drf_error("用户名或密码错误", status=401)

        # 4. 签发 Token
        access_ttl = getattr(settings, "ACCESS_TOKEN_EXPIRE_SECONDS", 86400)
        refresh_ttl = getattr(settings, "REFRESH_TOKEN_EXPIRE_SECONDS", 7 * 86400)
        at = AuthToken.objects.create(
            user=user,
            access_token=uuid.uuid4().hex,
            refresh_token=uuid.uuid4().hex,
            access_expires_at=timezone.now() + timezone.timedelta(seconds=access_ttl),
            refresh_expires_at=timezone.now() + timezone.timedelta(seconds=refresh_ttl),
        )

        return drf_ok({
            "accessToken": at.access_token,
            "refreshToken": at.refresh_token,
            "tokenType": "Bearer",
            "expiresIn": access_ttl,
        })

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
        # 尋达退出后残留并导致下次登录被 SessionAuthentication 强制校验 CSRF。
        try:
            django_logout(request)
        except Exception:
            pass
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
        # 建立新 session 后必须轮换 CSRF token，否则浏览器中旧的 csrftoken cookie
        # 与新 session 不匹配，后续 API 请求将报 "CSRF token incorrect"。
        rotate_token(request)
        logger.info(
            "[AuthViewSet][sso_session] 用户 %s 换取 Django Session 成功", user.username,
        )
        return drf_ok({"detail": "session 已建立，可继续 OIDC 授权"})
