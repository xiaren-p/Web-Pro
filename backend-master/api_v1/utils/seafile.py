"""Seafile 交互与缓存工具。

模块说明：封装获取/缓存 Seafile token 及相关辅助函数，供创建云账号流程使用。

重要函数：
- `get_cached_token(user, site)`：尝试从数据库读取有效的 CloudAuthToken
- `fetch_token_by_credentials(site, username, password)`：使用用户名/密码向 Seafile 认证接口请求 token
- `cache_token_for_user(user, site, token)`：将 token 持久化到 `CloudAuthToken`
"""

from django.utils import timezone
from django.conf import settings
from api_v1.models import CloudAuthToken
import requests
import re
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
