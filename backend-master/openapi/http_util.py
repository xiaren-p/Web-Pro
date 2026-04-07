#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""封装 Openapi的 http请求"""
import asyncio
import aiohttp
import orjson
from typing import Optional
from openapi.resp_schema import ResponseResult


class HttpBase(object):

    def __init__(self, default_timeout=30):
        self.default_timeout = default_timeout

    async def request(self, method: str, req_url: str,
                      params: Optional[dict] = None,
                      json: Optional[dict] = None,
                      headers: Optional[dict] = None,
                      **kwargs) -> ResponseResult:
        timeout = kwargs.pop('timeout', self.default_timeout)
        # Normalize timeout to aiohttp.ClientTimeout if numeric
        if isinstance(timeout, (int, float)):
            timeout = aiohttp.ClientTimeout(total=float(timeout))
        debug = kwargs.pop('debug', False)
        # 需要保持与加密算法一致的请求数据传递
        data = orjson.dumps(json, option=orjson.OPT_SORT_KEYS) if json else None
        # translate proxies dict to aiohttp proxy param; default from Django settings if not provided
        proxies = kwargs.pop('proxies', None)
        if proxies is None:
            try:
                from django.conf import settings
                proxies = getattr(settings, 'LINGXING_SDK_PROXIES', None)
            except Exception:
                proxies = None
        proxy = None
        if proxies and isinstance(proxies, dict):
            # choose proxy based on scheme
            if req_url.startswith('https://') and 'https' in proxies:
                proxy = proxies.get('https')
            elif req_url.startswith('http://') and 'http' in proxies:
                proxy = proxies.get('http')
            # fallback: if only one provided, use it
            if not proxy:
                proxy = proxies.get('https') or proxies.get('http')
        # trust_env default from settings if not explicitly provided
        trust_env = kwargs.pop('trust_env', None)
        if trust_env is None:
            try:
                from django.conf import settings
                trust_env = getattr(settings, 'LINGXING_SDK_TRUST_ENV', False)
            except Exception:
                trust_env = False
        if debug:
            print(f"[HttpBase] {method} {req_url}")
            print(f"[HttpBase] proxy={proxy} trust_env={trust_env} timeout={timeout}")
        try:
            async with aiohttp.ClientSession(trust_env=trust_env) as aio_session:
                async with aio_session.request(method=method, url=req_url, params=params, data=data,
                                               timeout=timeout, headers=headers, proxy=proxy, **kwargs) as resp:
                    if resp.status != 200:
                        raise ValueError(f"Response error, status code: {resp.status}, body: {await resp.text()}")
                    resp_json = await resp.json()
                    return ResponseResult(**resp_json)
        except (aiohttp.ClientConnectorError, aiohttp.ClientProxyConnectionError,
                aiohttp.ClientHttpProxyError, aiohttp.ServerTimeoutError,
                aiohttp.ClientOSError, asyncio.TimeoutError) as e:
            # Provide clearer context on proxy/timeout when failures occur
            raise ValueError(f"HTTP request failed: {method} {req_url}, proxy={proxy}, trust_env={trust_env}, "
                             f"timeout={timeout}: {e}") from e
