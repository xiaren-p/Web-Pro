"""身份认证业务服务。

封装登录、刷新令牌、登出、验证码生成与 SSO Session 建立等业务逻辑。
ViewSet 层仅负责请求解析与响应装配，全部业务编排委托至此模块。
"""
import logging
import uuid
import unicodedata

from django.conf import settings
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.middleware.csrf import rotate_token
from django.utils import timezone

from apps.system.models import AuthToken
from apps.common.utils.captcha import generate_captcha, validate_captcha

logger = logging.getLogger(__name__)


def normalize_captcha(text: str) -> str:
    """对验证码文本做 NFKC 归一化，用于大小写不敏感 + 全半角兼容比对。

    Args:
        text: 原始验证码文本。

    Returns:
        归一化后的小写 stripped 字符串。
    """
    if not text:
        return ""
    try:
        return unicodedata.normalize("NFKC", str(text)).strip().lower()
    except Exception:
        return str(text).strip().lower()


def validate_captcha_request(captcha_key: str, captcha_code: str, request) -> str | None:
    """验证图形验证码。返回 None 表示通过，否则返回错误信息字符串。

    验证顺序：
    1. 共享 cache 验证（validate_captcha）
    2. 万能验证码（ALLOW_CAPTCHA_BYPASS + CAPTCHA_MASTER_CODE）
    3. Session 回退验证

    Args:
        captcha_key: 验证码 key。
        captcha_code: 用户输入的验证码。
        request: DRF request 对象。

    Returns:
        None 表示验证通过；非空字符串为错误信息。
    """
    if validate_captcha(captcha_key, captcha_code):
        return None

    bypass_allowed = getattr(settings, "ALLOW_CAPTCHA_BYPASS", False)
    master_code = getattr(settings, "CAPTCHA_MASTER_CODE", None)
    if bypass_allowed and master_code and str(captcha_code) == str(master_code):
        return None

    sess_val = request.session.get(f"captcha:{captcha_key}")
    if not sess_val or not isinstance(sess_val, str) or not sess_val.strip():
        return "验证码错误"

    if normalize_captcha(sess_val) == normalize_captcha(captcha_code):
        try:
            del request.session[f"captcha:{captcha_key}"]
        except Exception:
            pass
        return None

    return "验证码错误"


def login(username: str, password: str, captcha_key: str, captcha_code: str, request) -> dict | tuple:
    """用户登录：验证码校验 → 账号密码认证 → 签发 Token。

    Args:
        username (str): 用户名。
        password (str): 密码。
        captcha_key (str): 验证码 key。
        captcha_code (str): 用户输入的验证码。
        request: DRF request 对象（用于验证码 session 回退）。

    Returns:
        dict: 成功时返回 token 信息 ``{accessToken, refreshToken, tokenType, expiresIn}``。
        tuple: 失败时返回 ``(error_msg, status_code)``。
    """
    if not captcha_key or not captcha_code:
        return ("验证码缺失", 400)
    if not username or not password:
        return ("用户名或密码不能为空", 400)

    captcha_err = validate_captcha_request(captcha_key, captcha_code, request)
    if captcha_err:
        return (captcha_err, 400)

    user = authenticate(username=username, password=password)
    if not user:
        return ("用户名或密码错误", 401)

    access_ttl = getattr(settings, "ACCESS_TOKEN_EXPIRE_SECONDS", 86400)
    refresh_ttl = getattr(settings, "REFRESH_TOKEN_EXPIRE_SECONDS", 7 * 86400)
    at = AuthToken.objects.create(
        user=user,
        access_token=uuid.uuid4().hex,
        refresh_token=uuid.uuid4().hex,
        access_expires_at=timezone.now() + timezone.timedelta(seconds=access_ttl),
        refresh_expires_at=timezone.now() + timezone.timedelta(seconds=refresh_ttl),
    )

    return {
        "accessToken": at.access_token,
        "refreshToken": at.refresh_token,
        "tokenType": "Bearer",
        "expiresIn": access_ttl,
    }


def refresh_token(token: str) -> dict | tuple:
    """刷新访问令牌。

    Args:
        token (str): 刷新令牌。

    Returns:
        dict: 成功时返回 ``{accessToken, tokenType, expiresIn}``。
        tuple: 失败时返回 ``(error_msg, status_code)``。
    """
    if not token:
        return ("缺少 refreshToken", 400)
    try:
        obj = AuthToken.objects.get(refresh_token=token, revoked=False)
    except AuthToken.DoesNotExist:
        return ("刷新令牌无效", 401)
    if not obj.is_refresh_valid():
        return ("刷新令牌已过期", 401)

    access_ttl = getattr(settings, 'ACCESS_TOKEN_EXPIRE_SECONDS', 86400)
    obj.access_token = uuid.uuid4().hex
    obj.access_expires_at = timezone.now() + timezone.timedelta(seconds=access_ttl)
    obj.save(update_fields=["access_token", "access_expires_at", "updated_at"])

    return {
        "accessToken": obj.access_token,
        "tokenType": "Bearer",
        "expiresIn": access_ttl,
    }


def logout(request) -> None:
    """用户登出：撤销 Bearer Token + 清除 Django Session。

    Args:
        request: DRF request 对象。
    """
    try:
        from rest_framework.authentication import get_authorization_header
        parts = get_authorization_header(request).split()
        if parts and len(parts) == 2 and parts[0].lower() == b"bearer":
            tok = parts[1].decode()
            AuthToken.objects.filter(access_token=tok, revoked=False).update(revoked=True)
    except Exception:
        pass
    try:
        django_logout(request)
    except Exception:
        pass


def generate_captcha_image(request) -> dict | tuple:
    """生成图形验证码并保存到 session。

    Args:
        request: DRF request 对象（用于 session 存储）。

    Returns:
        dict: 成功时返回 ``{img, uuid}``。
        tuple: 失败时返回 ``(error_msg, status_code)``。
    """
    try:
        key, img_b64, _text = generate_captcha()
    except Exception:
        return ("生成验证码失败", 500)

    try:
        request.session[f"captcha:{key}"] = _text
    except Exception:
        pass

    return {"img": img_b64, "uuid": key}


def establish_sso_session(request) -> tuple:
    """用已有 Bearer Token 换取 Django Session Cookie。

    前端在打开 Nextcloud SSO 链接前调用此接口，
    后端验证通过后建立 Django Session。

    Args:
        request: DRF request 对象（需已认证）。

    Returns:
        tuple: ``(detail_msg, status_code)``。
    """
    user = request.user
    if not user or not user.is_authenticated:
        return ("认证失败，请先登录系统", 401)

    django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    rotate_token(request)
    logger.info(
        "[AuthService] 用户 %s 换取 Django Session 成功", user.username,
    )
    return ("session 已建立，可继续 OIDC 授权", 200)
