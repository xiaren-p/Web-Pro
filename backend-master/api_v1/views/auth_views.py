"""身份认证视图（登录/登出/刷新 token 等）。

模块说明：提供用户登录、刷新 token、登出与图形验证码接口，包含对 Seafile 异步缓存的非阻塞触发。
"""

from django.contrib.auth import authenticate
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from django.conf import settings
import uuid
import json
import requests
from api_v1.models import AuthToken, DictItem
from api_v1.utils.responses import drf_ok, drf_error
# note: write_log calls removed per request; use centralized logging if needed
from api_v1.utils.captcha import generate_captcha, validate_captcha
from django.views.decorators.csrf import csrf_exempt

class AuthViewSet(viewsets.ViewSet):
    """身份认证相关接口（登录/登出/刷新 token 等）"""
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        action = getattr(self, 'action', None)
        # 允许匿名访问的动作：登录、图形验证码、刷新 token（刷新 token 使用 refreshToken 字段）
        if action in ("login", "captcha", "refresh_token"):
            return [AllowAny()]
        return super().get_permissions()

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

        # 尝试读取字典以获取 Seafile site；改为异步获取 token，避免阻塞登录响应
        seafile_cached = {"cached": False}
        try:
            site = None
            try:
                items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
                if items:
                    for it in items:
                        label = (it.label or "").lower()
                        val = (it.value or "").strip()
                        if not site and ("site" in label or "站" in label or val.startswith("http")):
                            site = val
                            break
                    if (not site) and items[0] and items[0].value:
                        try:
                            j = json.loads(items[0].value)
                            site = site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                        except Exception:
                            pass
            except Exception:
                site = None

            if site:
                try:
                    # 异步触发获取与缓存，不阻塞登录响应
                    import threading
                    from api_v1.utils.seafile import fetch_token_by_credentials, cache_token_for_user
                    def _bg_fetch_and_cache():
                        try:
                            token, err = fetch_token_by_credentials(site, username, password, timeout=4)
                            if token:
                                try:
                                    cache_token_for_user(user, site, token)
                                    pass
                                except Exception as e:
                                    pass
                            else:
                                pass
                        except Exception as e:
                            pass
                    threading.Thread(target=_bg_fetch_and_cache, daemon=True).start()
                    seafile_cached = {"cached": False, "msg": "pending"}
                except Exception as e:
                    seafile_cached = {"cached": False, "msg": f"seafile async start error: {e}"}
            else:
                seafile_cached = {"cached": False, "msg": "no site configured"}
        except Exception:
            seafile_cached = {"cached": False, "msg": "exception"}

        try:
            elapsed_ms = int((timezone.now() - t0).total_seconds() * 1000)
        except Exception:
            elapsed_ms = 0
        # login event logging removed
        resp = {
            "accessToken": at.access_token,
            "refreshToken": at.refresh_token,
            "tokenType": "Bearer",
            "expiresIn": access_ttl,
        }
        try:
            resp["seafileCached"] = bool(seafile_cached.get("cached", False)) if isinstance(seafile_cached, dict) else bool(seafile_cached)
            resp["seafileCachedDetail"] = seafile_cached
        except Exception:
            resp["seafileCached"] = False
            resp["seafileCachedDetail"] = {"cached": False}
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
        # 从 Authorization 提取当前 access token 并撤销
        try:
            from rest_framework.authentication import get_authorization_header
            parts = get_authorization_header(request).split()
            if parts and len(parts) == 2 and parts[0].lower() == b"bearer":
                tok = parts[1].decode()
                AuthToken.objects.filter(access_token=tok, revoked=False).update(revoked=True)
        except Exception:
            pass
        # logout logging removed
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
