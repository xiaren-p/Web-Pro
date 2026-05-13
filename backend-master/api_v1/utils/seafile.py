"""Seafile 交互与缓存工具。

模块说明：封装获取/缓存 Seafile token 及相关辅助函数，供创建云账号流程使用。

重要函数：
- `get_cached_token(user, site)`：尝试从数据库读取有效的 CloudAuthToken
- `fetch_token_by_credentials(site, username, password)`：使用用户名/密码向 Seafile 认证接口请求 token
- `cache_token_for_user(user, site, token)`：将 token 持久化到 `CloudAuthToken`
- `get_or_refresh_admin_token(site, admin_user, admin_pass)`：获取管理员 token（优先从 Django cache 读取，过期自动刷新）
"""

from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from api_v1.models import CloudAuthToken
import hashlib
import requests
import re
from urllib.parse import quote
from django.utils import timezone as dj_timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# 全局复用的会话（连接池 + 重试策略）
_SESSION = None


def _get_session():
    """返回复用的 requests.Session 实例，并在首次创建时安装重试/连接池配置。"""
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    s = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=20,
        pool_maxsize=50,
        max_retries=Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET", "POST", "PUT"),
        ),
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    _SESSION = s
    return _SESSION


def _normalize_site(site: str):
    """规范化 Seafile site 字符串，返回 (base_site, auth_url)。"""
    base_site = str(site).strip()
    if not re.match(r"^https?://", base_site, re.I):
        base_site = "https://" + base_site
    auth_url = base_site.rstrip('/')
    if not re.search(r"api2/auth-token", auth_url, re.I):
        auth_url = auth_url + "/api2/auth-token/"
    return base_site, auth_url


def get_cached_token(user, site):
    """尝试从 `CloudAuthToken` 中读取未过期的 token，未命中返回 None。"""
    try:
        base_site, _ = _normalize_site(site)
        site_key = base_site.rstrip('/')
        objs = CloudAuthToken.objects.filter(user=user)
        now = dj_timezone.now()
        for obj in objs:
            try:
                if (obj.site or '').rstrip('/') != site_key:
                    continue
                if not (obj and obj.token and obj.expires_at):
                    continue
                exp = obj.expires_at
                try:
                    if dj_timezone.is_naive(exp):
                        exp = dj_timezone.make_aware(exp, dj_timezone.get_default_timezone())
                    if exp > now:
                        # logging removed
                        return obj.token
                except Exception:
                    try:
                        if obj.expires_at > now:
                            # logging removed (fallback)
                            return obj.token
                    except Exception:
                        pass
            except Exception:
                continue
    except Exception:
        pass
    return None


def fetch_token_by_credentials(site, username, password, timeout=6):
    """使用用户名/密码向 Seafile 获取 token，返回 (token, error_or_None)。"""
    try:
        base_site, auth_url = _normalize_site(site)
        resp = _get_session().post(
            auth_url,
            json={"username": username, "password": password},
            timeout=timeout,
        )
        if 200 <= resp.status_code < 300:
            try:
                token = resp.json().get('token')
            except Exception:
                token = None
            if token:
                return token, None
            return None, 'no token in response'
        return None, f'seafile status {resp.status_code}'
    except Exception as e:
        return None, f'request error: {e}'


def cache_token_for_user(user, site, token):
    """将 token 持久化到 `CloudAuthToken`（若已存在则更新）。"""
    try:
        base_site, _ = _normalize_site(site)
        site_key = base_site.rstrip('/')
        ttl = int(getattr(settings, 'CLOUD_TOKEN_EXPIRE_SECONDS', 3600))
        expires = timezone.now() + timezone.timedelta(seconds=ttl)
        try:
            CloudAuthToken.objects.update_or_create(user=user, defaults={'site': site_key, 'token': token, 'expires_at': expires})
        except Exception:
            try:
                obj = CloudAuthToken.objects.filter(user=user).first()
                if obj:
                    obj.site = site_key
                    obj.token = token
                    obj.expires_at = expires
                    obj.save()
                else:
                    CloudAuthToken.objects.create(user=user, site=site_key, token=token, expires_at=expires)
            except Exception:
                # logging removed on failure
                return False
        # logging removed on success
        return True
    except Exception:
        return False


# ── 管理员 Token 自动刷新（面向后端服务，不绑定具体用户）──────────────────────

# Django cache 的 key 前缀，避免与其他 key 碰撞
_ADMIN_TOKEN_CACHE_PREFIX = "seafile_admin_token:"



def _admin_token_cache_key(site: str) -> str:
    """根据 site 生成稳定的 cache key，避免 URL 拼写差异导致误判。"""
    base_site, _ = _normalize_site(site)
    site_hash = hashlib.md5(base_site.rstrip("/").encode()).hexdigest()[:12]
    return f"{_ADMIN_TOKEN_CACHE_PREFIX}{site_hash}"


def get_or_refresh_admin_token(site: str, admin_user: str, admin_pass: str, ttl: int = 3600):
    """获取 Seafile 管理员 Token，优先读 Django cache，过期自动刷新。

    刷新策略：
    1. 尝试从 Django cache（Redis）中读取未过期的 token；命中直接返回。
    2. cache miss → 使用配置的 ``admin_user`` / ``admin_pass`` 重新向 Seafile
       ``/api2/auth-token/`` 认证，成功后将新 token 写入 cache（TTL 由调用方
       从系统参数配置表读取后通过 ``ttl`` 参数传入，默认 3600 秒）。
    3. 认证失败时返回 ``(None, error_message)``。

    Args:
        site (str): Seafile 站点地址，如 ``"https://seafile.example.com"``。
        admin_user (str): 管理员账号（Email）。
        admin_pass (str): 管理员密码。
        ttl (int): token 缓存时长（秒），由调用方从 Config 表读取后传入，默认 3600。

    Returns:
        tuple[str | None, str | None]: ``(token, error_msg)``，
        成功时 ``error_msg`` 为 ``None``；失败时 ``token`` 为 ``None``。
    """
    cache_key = _admin_token_cache_key(site)

    # 第一步：读 cache
    cached = cache.get(cache_key)
    if cached:
        return cached, None

    # 第二步：cache miss，重新认证
    token, err = fetch_token_by_credentials(site, admin_user, admin_pass)
    if err:
        return None, err

    # 第三步：写 cache（留 60s 余量，防止临界过期）
    cache.set(cache_key, token, timeout=max(ttl - 60, 60))
    return token, None


def invalidate_admin_token(site: str) -> None:
    """主动清除 Seafile 管理员 token 缓存（例如收到 401 后强制刷新时调用）。

    Args:
        site (str): Seafile 站点地址。
    """
    cache_key = _admin_token_cache_key(site)
    cache.delete(cache_key)


def delete_seafile_account(site: str, token: str, email: str) -> tuple:
    """通过管理员 token 删除 Seafile 上指定邮箱的账号。

    调用 Seafile ``DELETE /api2/accounts/{email}/`` 接口。若账号不存在（404）
    视为已删除，同样返回成功，保证幂等。

    Args:
        site (str): Seafile 站点地址，如 ``"https://seafile.example.com"``。
        token (str): 有效的 Seafile 管理员 token。
        email (str): 待删除账号的邮箱地址。

    Returns:
        tuple[bool, str | None]: ``(success, error_msg)``，
        成功或账号已不存在时返回 ``(True, None)``；失败时返回 ``(False, error_msg)``。
    """
    base_site, _ = _normalize_site(site)
    url = base_site.rstrip("/") + f"/api2/accounts/{quote(email)}/"
    headers = {"Authorization": f"Token {token}"}
    try:
        resp = requests.delete(url, headers=headers, timeout=10)
        # 200 / 204 代表成功删除，404 代表账号不存在（同样视为成功）
        if resp.status_code in (200, 204, 404):
            return True, None
        return False, f"seafile 返回 {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"请求失败: {e}"
