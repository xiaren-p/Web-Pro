#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
提供一个在后台线程运行的 asyncio loop，用于同步访问 TokenManager。

说明：
- 在传统同步 Django 环境中，直接调用异步 TokenManager 比较麻烦；本模块创建一个后台线程并运行 asyncio 事件循环，
  然后在该事件循环中初始化 `TokenManager` 单例。外部可以通过 `get_access_token()` 同步地获取 access_token。
- 使用 `concurrent.futures.Future` + `asyncio.run_coroutine_threadsafe` 实现线程间协作。
"""
import threading
import asyncio
import time
from typing import Optional

from openapi.token_manager import TokenManager


class SyncTokenManager:
    """线程安全的同步 Token 管理器外壳。

    用法：
        mgr = SyncTokenManager.get_instance(host, app_id, app_secret)
        token = mgr.get_access_token()
    """

    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls, host: str = None, app_id: str = None, app_secret: str = None, proxies: Optional[dict] = None):
        with cls._instance_lock:
            if cls._instance is None:
                if not (host and app_id and app_secret):
                    raise ValueError("首次初始化 SyncTokenManager 必须提供 host/app_id/app_secret")
                cls._instance = SyncTokenManager(host, app_id, app_secret, proxies)
            return cls._instance

    def __init__(self, host: str, app_id: str, app_secret: str, proxies: Optional[dict] = None):
        self._host = host
        self._app_id = app_id
        self._app_secret = app_secret
        self._proxies = proxies
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._ready_event = threading.Event()
        self._token_manager = None
        self._thread.start()
        # 等待后台事件循环初始化完成 TokenManager
        if not self._ready_event.wait(timeout=10):
            raise RuntimeError("启动后台事件循环超时")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)

        async def _init():
            # 在事件循环内初始化异步 TokenManager 单例
            tm = await TokenManager.get_instance(host=self._host, app_id=self._app_id, app_secret=self._app_secret, proxies=self._proxies)
            self._token_manager = tm
            self._ready_event.set()
            # 保持协程运行以便后续任务执行
            while True:
                await asyncio.sleep(3600)

        try:
            self._loop.run_until_complete(_init())
        except Exception:
            self._ready_event.set()
            raise

    def get_access_token(self, safety_margin: int = 60, timeout: Optional[float] = 10, **kwargs) -> str:
        """同步获取 access_token，会等待异步任务完成。

        如果 `timeout` 为 None，则表示等待直到完成（不超时）。
        """
        if not self._token_manager:
            raise RuntimeError("TokenManager 尚未初始化")
        coro = self._token_manager.get_access_token(safety_margin=safety_margin, **kwargs)
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if timeout is None:
            return fut.result()
        return fut.result(timeout)

    def force_refresh(self, timeout: Optional[float] = 10, **kwargs) -> str:
        if not self._token_manager:
            raise RuntimeError("TokenManager 尚未初始化")
        coro = self._token_manager.force_refresh(**kwargs)
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if timeout is None:
            return fut.result()
        return fut.result(timeout)

    def start_auto_refresh(self, check_interval: int = 5, safety_margin: int = 60, **kwargs):
        if not self._token_manager:
            raise RuntimeError("TokenManager 尚未初始化")
        # 在后台 loop 中调用 start_auto_refresh（该方法是同步的，但内部使用 loop.create_task）
        def _call():
            self._token_manager.start_auto_refresh(check_interval=check_interval, safety_margin=safety_margin, **kwargs)

        self._loop.call_soon_threadsafe(_call)

    def stop_auto_refresh(self):
        if not self._token_manager:
            return
        def _call():
            self._token_manager.stop_auto_refresh()

        self._loop.call_soon_threadsafe(_call)


__all__ = ["SyncTokenManager"]
