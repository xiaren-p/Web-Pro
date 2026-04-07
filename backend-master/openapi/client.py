#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
同步友好的 LingXing API 客户端封装。

用法示例（同步调用）：
    from openapi.client import LingXingClient
    client = LingXingClient()
    resp = client.request_sync("/api/your/route", "GET", req_params={})

该客户端内部使用 `SyncTokenManager` 获取 access_token 并调用 `OpenApiBase.request`。
"""
from typing import Optional
import asyncio

from openapi.openapi import OpenApiBase
from openapi.sync_token_manager import SyncTokenManager
from django.conf import settings


class LingXingClient:
    def __init__(self, host: Optional[str] = None, app_id: Optional[str] = None, app_secret: Optional[str] = None, proxies: Optional[dict] = None):
        self.host = host or getattr(settings, 'LINGXING_SDK_API_BASE_URL', None)
        self.app_id = app_id or getattr(settings, 'LINGXING_SDK_APP_ID', None)
        self.app_secret = app_secret or getattr(settings, 'LINGXING_SDK_APP_SECRET', None)
        self.proxies = proxies
        if not (self.host and self.app_id and self.app_secret):
            raise ValueError("LingXingClient 初始化需要 host/app_id/app_secret")

        # SyncTokenManager 在 app 启动时已初始化（如果配置），这里尝试获取已存在实例或创建新实例
        self._sync_mgr = SyncTokenManager.get_instance(host=self.host, app_id=self.app_id, app_secret=self.app_secret, proxies=proxies)
        self._api = OpenApiBase(host=self.host, app_id=self.app_id, app_secret=self.app_secret, proxies=proxies)

    def request_sync(self, route_name: str, method: str, req_params: Optional[dict] = None, req_body: Optional[dict] = None, timeout: Optional[float] = None, **kwargs):
        """同步请求：自动获取 access_token 并调用 OpenApiBase.request。

        如果传入 `timeout` 为 None，则表示等待直到完成（不超时）。
        """
        access_token = self._sync_mgr.get_access_token(timeout=timeout)
        # 在后台事件循环中执行异步请求并等待结果
        coro = self._api.request(access_token, route_name, method, req_params=req_params, req_body=req_body, **kwargs)
        fut = asyncio.run_coroutine_threadsafe(coro, self._sync_mgr._loop)
        if timeout is None:
            return fut.result()
        return fut.result(timeout)


__all__ = ["LingXingClient"]
