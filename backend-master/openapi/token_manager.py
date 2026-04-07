#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
全局 AccessToken 管理器（支持自动刷新）

说明（中文注释）：
- 提供一个基于内存的单例式 Token 管理器，用于管理 LingXing OpenAPI 的 `access_token` 和 `refresh_token`。
- 在异步上下文中使用：调用 `await TokenManager.get_instance().get_access_token()` 获取可用的 access_token。
- 当 token 即将过期（默认提前 60 秒）时，会在下一次请求时自动刷新；也可以启用后台自动刷新任务 `start_auto_refresh()`。

注意：该管理器使用内存缓存，服务重启后会丢失。若需要持久化，请在外部实现保存/加载逻辑。
"""
import asyncio
import time
from typing import Optional

from openapi.openapi import OpenApiBase
from openapi.resp_schema import AccessTokenDto


class TokenManager:
    """简单的异步 Token 管理器（线程安全，基于 asyncio）

    主要方法：
    - get_access_token(): 获取有效的 access_token（会在必要时自动刷新）
    - force_refresh(): 强制从服务端获取新的 token
    - start_auto_refresh(): 启动后台任务，主动在 token 到期前刷新
    - stop_auto_refresh(): 停止后台任务
    """

    _instance = None
    _instance_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, host: str = None, app_id: str = None, app_secret: str = None, proxies: Optional[dict] = None):
        """返回单例实例；首次调用需传入 host/app_id/app_secret 来初始化。"""
        async with cls._instance_lock:
            if cls._instance is None:
                if not (host and app_id and app_secret):
                    raise ValueError("首次初始化 TokenManager 必须提供 host, app_id, app_secret")
                cls._instance = TokenManager(host, app_id, app_secret, proxies)
            return cls._instance

    def __init__(self, host: str, app_id: str, app_secret: str, proxies: Optional[dict] = None):
        self._client = OpenApiBase(host=host, app_id=app_id, app_secret=app_secret, proxies=proxies)
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expiry_ts: float = 0.0
        self._lock = asyncio.Lock()
        self._bg_task: Optional[asyncio.Task] = None
        self._stopping = False

    async def _update_from_dto(self, dto: AccessTokenDto):
        now = time.time()
        self._access_token = dto.access_token
        self._refresh_token = dto.refresh_token
        # 过期时间点，提前 0 秒算起；外部读取时会再减去 safety_margin
        self._expiry_ts = now + int(dto.expires_in)

    async def force_refresh(self, proxies: Optional[dict] = None, **kwargs) -> str:
        """强制从服务端获取新的 access_token（不使用 refresh_token）"""
        async with self._lock:
            dto = await self._client.generate_access_token(proxies=proxies, **kwargs)
            await self._update_from_dto(dto)
            return self._access_token

    async def _refresh_with_refresh_token(self, proxies: Optional[dict] = None, **kwargs) -> str:
        """使用 refresh_token 去续约；失败时抛异常给调用方（调用方可回退到 generate_access_token）。"""
        if not self._refresh_token:
            raise ValueError("没有可用的 refresh_token")
        dto = await self._client.refresh_token(self._refresh_token, proxies=proxies, **kwargs)
        await self._update_from_dto(dto)
        return self._access_token

    async def get_access_token(self, safety_margin: int = 60, proxies: Optional[dict] = None, **kwargs) -> str:
        """返回可用的 access_token；如果快过期会自动续约或重新获取。safety_margin 单位秒。"""
        now = time.time()
        async with self._lock:
            # token 仍然有效
            if self._access_token and now < (self._expiry_ts - safety_margin):
                return self._access_token

            # 尝试用 refresh_token 续约
            if self._refresh_token:
                try:
                    return await self._refresh_with_refresh_token(proxies=proxies, **kwargs)
                except Exception:
                    # 如果 refresh 失败，继续回退到重新生成
                    pass

            # 兜底：重新生成 access_token
            dto = await self._client.generate_access_token(proxies=proxies, **kwargs)
            await self._update_from_dto(dto)
            return self._access_token

    def start_auto_refresh(self, check_interval: int = 5, safety_margin: int = 60, proxies: Optional[dict] = None, **kwargs):
        """启动后台自动刷新任务：每 `check_interval` 秒检查一次；当距离过期不足 `safety_margin` 秒时触发刷新。

        说明：调用者应在 ASGI 启动或可用事件循环中调用该方法。
        """
        if self._bg_task and not self._bg_task.done():
            return

        loop = asyncio.get_event_loop()

        async def _bg():
            while not self._stopping:
                try:
                    now = time.time()
                    ttl = self._expiry_ts - now
                    if self._access_token and ttl <= safety_margin:
                        try:
                            await self.get_access_token(safety_margin=safety_margin, proxies=proxies, **kwargs)
                        except Exception:
                            # 忽略单次刷新失败，下一轮继续尝试
                            pass
                    await asyncio.sleep(check_interval)
                except asyncio.CancelledError:
                    break

        self._stopping = False
        self._bg_task = loop.create_task(_bg())

    def stop_auto_refresh(self):
        """停止后台自动刷新任务。"""
        self._stopping = True
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
        self._bg_task = None


__all__ = ["TokenManager"]
