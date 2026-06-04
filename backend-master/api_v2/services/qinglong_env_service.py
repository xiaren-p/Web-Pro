"""青龙面板环境变量同步服务（qinglong_env_service）。

职责：
  1. 从系统参数（Config 模型）读取青龙 OpenAPI 接入配置。
  2. 通过 /open/auth/token 获取访问令牌。
  3. 通过 /open/envs 拉取指定名称的环境变量值。
  4. 将结果写入 Django Cache，TTL = 600 秒（10 分钟），
     供其他模块通过 get_cached_env() 直接消费，无需重复请求青龙。

缓存键规则：
  qinglong:env:{ENV_VAR_NAME}，例如 qinglong:env:LX_ERP_HEADERS
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

# 青龙 OpenAPI 配置在 Config 模型中的键名
_CFG_URL = "QINGLONG_URL"
_CFG_CLIENT_ID = "QINGLONG_CLIENT_ID"
_CFG_CLIENT_SECRET = "QINGLONG_CLIENT_SECRET"
_CFG_TASK_ID = "QINGLONG_REFRESH_MIDDLE_API_AUTH_TASK"

# 需要定期同步并缓存的环境变量名列表
TARGET_ENV_NAMES: list[str] = [
    "LX_ERP_HEADERS",
    "LX_ADS_HEADERS",
    "MIDDLE_API_HEADERS",
]

# Django Cache 缓存 TTL（秒）
_CACHE_TTL = 600

# 缓存键前缀
_CACHE_PREFIX = "qinglong:env:"


def _get_config_value(key: str) -> str:
    """从 Config 模型中读取参数明文值。

    仅在有 Config 数据库时调用，捕获全部异常以避免影响调用方。

    Args:
        key (str): Config.key 键名。

    Returns:
        str: 参数明文值，读取失败时返回空字符串。
    """
    try:
        from api_v1.models.system.config import Config
        cfg = Config.objects.filter(key=key, status=True).first()
        if cfg is None:
            return ""
        return cfg.get_plaintext_value()
    except Exception as exc:
        logger.warning("[QinglongEnvService] 读取 Config 失败: key=%s err=%s", key, exc)
        return ""


def _fetch_token(base_url: str, client_id: str, client_secret: str) -> str:
    """向青龙 OpenAPI 获取访问令牌。

    接口：GET {base_url}/open/auth/token?client_id=&client_secret=
    响应：{"code": 200, "data": {"token": "...", ...}}

    Args:
        base_url (str): 青龙面板地址，如 http://192.168.0.10:5700。
        client_id (str): OpenAPI client_id。
        client_secret (str): OpenAPI client_secret。

    Returns:
        str: access token；失败时返回空字符串。

    Raises:
        requests.RequestException: 网络或 HTTP 错误时向上传播，由调用方记录日志。
    """
    url = f"{base_url.rstrip('/')}/open/auth/token"
    resp = requests.get(
        url,
        params={"client_id": client_id, "client_secret": client_secret},
        timeout=10,
    )
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()
    if payload.get("code") != 200:
        raise ValueError(
            f"青龙 /open/auth/token 返回非 200: code={payload.get('code')} "
            f"message={payload.get('message', '')}"
        )
    token: str = payload["data"]["token"]
    logger.debug("[QinglongEnvService] 获取 token 成功, client_id=%s", client_id)
    return token


def _fetch_envs(base_url: str, token: str, names: list[str]) -> dict[str, str]:
    """从青龙面板批量拉取指定名称的环境变量值。

    接口：GET {base_url}/open/envs
    响应：{"code": 200, "data": [{"name": "VAR_NAME", "value": "...", ...}]}
    通过响应列表按 name 字段匹配目标变量，返回 {name: value} 字典。

    Args:
        base_url (str): 青龙面板地址。
        token (str): Bearer 访问令牌。
        names (list[str]): 需要拉取的环境变量名称列表。

    Returns:
        dict[str, str]: {变量名: 变量值} 字典，缺失变量不会出现在结果中。

    Raises:
        requests.RequestException: 网络或 HTTP 错误时向上传播。
        ValueError: 青龙 API 返回非 200 时抛出。
    """
    url = f"{base_url.rstrip('/')}/open/envs"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()
    if payload.get("code") != 200:
        raise ValueError(
            f"青龙 /open/envs 返回非 200: code={payload.get('code')} "
            f"message={payload.get('message', '')}"
        )

    name_set = set(names)
    result: dict[str, str] = {}
    for item in payload.get("data", []):
        item_name: str = item.get("name", "")
        if item_name in name_set:
            result[item_name] = item.get("value", "")

    return result


def refresh_all() -> dict[str, str]:
    """拉取全部目标环境变量并写入缓存。

    完整流程：
      1. 从 Config 读取青龙接入配置（URL / client_id / client_secret）。
      2. 若配置不完整则跳过，记录警告后返回空字典。
      3. 获取 token → 拉取环境变量 → 写 Django Cache（TTL 600 s）。
      4. 无论成功与否，均捕获异常并记录 ERROR 日志，不向上传播，
         保证 Beat 任务不会因网络抖动而崩溃。

    Returns:
        dict[str, str]: 本次成功写入缓存的 {变量名: 变量值} 字典；失败时返回空字典。
    """
    base_url = _get_config_value(_CFG_URL)
    client_id = _get_config_value(_CFG_CLIENT_ID)
    client_secret = _get_config_value(_CFG_CLIENT_SECRET)

    if not all([base_url, client_id, client_secret]):
        logger.warning(
            "[QinglongEnvService] [refresh_all] 青龙配置不完整，跳过同步。"
            "请在系统参数配置中填写 %s / %s / %s",
            _CFG_URL, _CFG_CLIENT_ID, _CFG_CLIENT_SECRET,
        )
        return {}

    try:
        token = _fetch_token(base_url, client_id, client_secret)
        env_map = _fetch_envs(base_url, token, TARGET_ENV_NAMES)

        for name, value in env_map.items():
            cache.set(f"{_CACHE_PREFIX}{name}", value, timeout=_CACHE_TTL)
            logger.info(
                "[QinglongEnvService] [refresh_all] 环境变量已缓存: name=%s value_len=%d",
                name,
                len(value),
            )

        missing = set(TARGET_ENV_NAMES) - set(env_map.keys())
        if missing:
            logger.warning(
                "[QinglongEnvService] [refresh_all] 青龙中未找到以下变量: %s",
                ", ".join(missing),
            )

        return env_map

    except requests.RequestException as exc:
        logger.error(
            "[QinglongEnvService] [refresh_all] 网络请求失败: %s",
            exc,
            exc_info=True,
        )
    except ValueError as exc:
        logger.error(
            "[QinglongEnvService] [refresh_all] 青龙 API 返回异常: %s",
            exc,
            exc_info=True,
        )
    except Exception as exc:
        logger.error(
            "[QinglongEnvService] [refresh_all] 未知异常: %s",
            exc,
            exc_info=True,
        )

    return {}


def refresh_with_task_trigger() -> dict[str, str]:
    """先触发青龙定时任务，再拉取最新环境变量写入缓存。

    从前端系统参数 QINGLONG_TASK_NAME 读取任务名，搜索并执行。
    若未配置则降级为普通刷新。

    Returns:
        dict[str, str]: 刷新后的 {变量名: 变量值} 字典；失败时返回空字典。
    """
    task_id_str = _get_config_value(_CFG_TASK_ID)
    base_url = _get_config_value(_CFG_URL)
    client_id = _get_config_value(_CFG_CLIENT_ID)
    client_secret = _get_config_value(_CFG_CLIENT_SECRET)

    if not all([base_url, client_id, client_secret]):
        logger.warning("[QinglongEnvService] 青龙配置不完整，跳过")
        return {}
    if not task_id_str:
        logger.warning("[QinglongEnvService] QINGLONG_REFRESH_MIDDLE_API_AUTH_TASK 未配置，降级为普通刷新")
        return refresh_all()

    try:
        task_id = int(task_id_str)
    except (ValueError, TypeError):
        logger.error("[QinglongEnvService] QINGLONG_REFRESH_MIDDLE_API_AUTH_TASK 不是有效数字: %s", task_id_str)
        return refresh_all()

    try:
        token = _fetch_token(base_url, client_id, client_secret)
        logger.info("[QinglongEnvService] 触发青龙任务 id=%d", task_id)
        requests.put(
            f"{base_url.rstrip('/')}/open/crons/{task_id}/run",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        time.sleep(5)
    except Exception:
        logger.exception("[QinglongEnvService] 触发青龙任务失败，降级为普通刷新")

    return refresh_all()


def get_cached_env(name: str) -> str:
    """获取单个已缓存的环境变量值。

    仅读缓存，不触发网络请求。若缓存中不存在（如首次启动或 TTL 已过期）
    则返回空字符串，调用方需自行处理降级逻辑。

    Args:
        name (str): 环境变量名，如 "LX_ERP_HEADERS"。

    Returns:
        str: 缓存的变量值；未命中时返回空字符串。
    """
    value: str | None = cache.get(f"{_CACHE_PREFIX}{name}")
    if value is None:
        logger.debug(
            "[QinglongEnvService] [get_cached_env] 缓存未命中: name=%s", name
        )
        return ""
    return value
