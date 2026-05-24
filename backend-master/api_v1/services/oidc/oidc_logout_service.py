"""OIDC Back-Channel Logout 服务（oidc_logout_service）。

当主系统用户退出登录时，向 Nextcloud user_oidc 插件发送后端频道注销令牌（Logout Token），
实现服务端主动推送的无感 SSO 同步注销。

规范参考：OpenID Connect Back-Channel Logout 1.0
https://openid.net/specs/openid-connect-backchannel-1_0.html
"""
import logging
import time
import uuid

import jwt
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# NC user_oidc 后端频道注销端点路径
_BCL_PATH = "/apps/user_oidc/backchannel-logout"

# NC OIDC Application 名称，与 setup_nc_oidc_client 保持一致
_NC_APP_NAME = "Nextcloud SSO"


def _get_nc_base_url() -> str:
    """从 Config 表读取 NC 基础 URL。

    Returns:
        str: NC 基础 URL，已去除末尾斜杠。

    Raises:
        RuntimeError: Config 表中 NC_BASE_URL 不存在或为空。
    """
    from api_v1.models.system.config import Config

    conf = Config.objects.filter(config_key="NC_BASE_URL").first()
    if not conf or not conf.config_value:
        raise RuntimeError("[oidc_logout_service] Config 表中缺少 NC_BASE_URL 配置")
    return conf.config_value.strip().rstrip("/")


def _get_nc_client_id() -> str:
    """从 oauth2_provider Application 表获取 NC OIDC client_id。

    Returns:
        str: NC OIDC Application 的 client_id。

    Raises:
        RuntimeError: Application 记录不存在或 oauth2_provider 未安装。
    """
    try:
        from oauth2_provider.models import Application
    except ImportError as exc:
        raise RuntimeError("[oidc_logout_service] oauth2_provider 未安装") from exc

    app = Application.objects.filter(name=_NC_APP_NAME).first()
    if not app:
        raise RuntimeError(
            f"[oidc_logout_service] 未找到名为 '{_NC_APP_NAME}' 的 OAuth Application，"
            "请先执行 python manage.py setup_nc_oidc_client。"
        )
    return app.client_id


def _derive_issuer(request=None) -> str:
    """推导 OIDC 颁发者 URL。

    优先使用 OAUTH2_PROVIDER['OIDC_ISS_ENDPOINT']（固定配置），
    其次从 request.build_absolute_uri('/') 动态推导（与 DOT 生成 id_token 时完全一致）。

    Args:
        request: Django HttpRequest 实例（可选）。

    Returns:
        str: issuer 字符串。

    Raises:
        RuntimeError: 两种来源均不可用时抛出。
    """
    # 优先固定配置
    oauth2_cfg: dict = getattr(settings, "OAUTH2_PROVIDER", {})
    issuer: str = (oauth2_cfg.get("OIDC_ISS_ENDPOINT") or "").strip()
    if issuer:
        return issuer

    # 从 request 动态推导（与 DOT ConnectDiscoveryInfoView 逻辑一致）
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")

    raise RuntimeError(
        "[oidc_logout_service] 无法推导 OIDC issuer：既未配置 OIDC_ISS_ENDPOINT，"
        "也未传入 request 对象。"
    )


def push_backchannel_logout(user, request=None) -> None:
    """向 Nextcloud 推送 OIDC Back-Channel Logout Token，同步注销 NC 端会话。

    构建并以 RSA 私钥签名符合 OIDC BCL 1.0 规范的 Logout Token，POST 至
    NC user_oidc 的后端频道注销端点。调用失败时仅记录日志，不向上抛出异常，
    保证主系统退出流程不受任何阻断。

    Args:
        user: 已认证的 Django User 实例，用于提取 sub（user.pk）声明。
        request: Django HttpRequest 实例，用于动态推导 issuer（与 id_token 保持一致）。

    Returns:
        None

    说明：
        Logout Token 必要声明（BCL 1.0 §2.4）：
        - iss  ：OIDC 颁发者 URL，与 id_token 中完全一致。
        - sub  ：用户唯一标识（user.pk 字符串），与 id_token 中一致。
        - aud  ：受众，即 NC 的 client_id。
        - iat  ：签发时间戳。
        - jti  ：唯一标识符，防重放。
        - events：固定键 "http://schemas.openid.net/event/backchannel-logout"。
    """
    try:
        # -- 前置检查 --
        private_key: str = (getattr(settings, "OAUTH2_PROVIDER", {}) or {}).get(
            "OIDC_RSA_PRIVATE_KEY", ""
        )
        if not private_key:
            logger.warning(
                "[oidc_logout_service][push_backchannel_logout] "
                "OIDC RSA 私钥未配置，跳过 NC Back-Channel Logout。"
            )
            return

        issuer = _derive_issuer(request)
        nc_base_url = _get_nc_base_url()
        client_id = _get_nc_client_id()
        verify_ssl: bool = getattr(settings, "NC_VERIFY_SSL", True)

        # -- 构造 Logout Token（OIDC BCL 1.0 §2.4）--
        payload = {
            "iss": issuer,
            "sub": str(user.pk),
            "aud": client_id,
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
            "events": {
                "http://schemas.openid.net/event/backchannel-logout": {}
            },
        }

        logout_token: str = jwt.encode(payload, private_key, algorithm="RS256")

        # -- POST 至 NC 后端频道注销端点 --
        url = f"{nc_base_url}{_BCL_PATH}"
        resp = requests.post(
            url,
            data={"logout_token": logout_token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            verify=verify_ssl,
            timeout=10,
        )

        if resp.status_code == 200:
            logger.info(
                "[oidc_logout_service][push_backchannel_logout] NC 注销成功 user=%s",
                user.username,
            )
        else:
            logger.warning(
                "[oidc_logout_service][push_backchannel_logout] "
                "NC 返回非 200 user=%s status=%s body=%s",
                user.username,
                resp.status_code,
                resp.text[:300],
            )

    except Exception as exc:
        # 注销推送失败不阻断主系统退出，仅记录完整堆栈
        logger.error(
            "[oidc_logout_service][push_backchannel_logout] "
            "NC 注销推送异常 user=%s err=%s",
            getattr(user, "username", "?"),
            exc,
            exc_info=True,
        )
