#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""封装Openapi基础操作"""
import copy
import time
from typing import Optional

from openapi.http_util import HttpBase
from openapi.resp_schema import AccessTokenDto, ResponseResult
from openapi.sign import SignBase


class OpenApiBase(object):

    def __init__(self, host: str, app_id: str, app_secret: str, proxies: Optional[dict] = None):
        self.host = host
        self.app_id = app_id
        self.app_secret = app_secret
        # 全局代理（默认用于所有请求，除非单次调用显式传入 proxies 覆盖）
        self.proxies = proxies

    async def generate_access_token(self, proxies: Optional[dict] = None, **kwargs) -> AccessTokenDto:
        """
        获取 access_token
        :param proxies: 代理字典，例如 {"http": "http://user:pass@host:port", "https": "http://user:pass@host:port"}；默认使用构造函数传入的全局代理
        :param kwargs: 其他参数（如 timeout、ssl=False、debug=True 等）
        """
        path = '/api/auth-server/oauth/access-token'
        req_url = self.host + path
        req_params = {
            "appId": self.app_id,
            "appSecret": self.app_secret,
        }
        effective_proxies = self.proxies if proxies is None else proxies
        resp_result = await HttpBase().request("POST", req_url, params=req_params, proxies=effective_proxies, **kwargs)
        if resp_result.code != 200:
            error_msg = f"generate_access_token failed, reason: {resp_result.message}"
            raise ValueError(error_msg)

        assert isinstance(resp_result.data, dict)
        return AccessTokenDto(**resp_result.data)

    async def refresh_token(self, refresh_token: str, proxies: Optional[dict] = None, **kwargs) -> AccessTokenDto:
        """续约access-token
        :param refresh_token: 刷新令牌
        :param proxies: 代理字典；默认使用构造函数传入的全局代理
        :param kwargs: 其他参数（如 timeout、ssl=False、debug=True 等）
        """
        path = '/api/auth-server/oauth/refresh'
        req_url = self.host + path
        req_params = {
            "appId": self.app_id,
            "refreshToken": refresh_token,
        }
        effective_proxies = self.proxies if proxies is None else proxies
        resp_result = await HttpBase().request("POST", req_url, params=req_params, proxies=effective_proxies, **kwargs)
        if resp_result.code != 200:
            error_msg = f"refresh_token failed, reason: {resp_result.message}"
            raise ValueError(error_msg)

        assert isinstance(resp_result.data, dict)
        return AccessTokenDto(**resp_result.data)

    async def request(self, access_token: str, route_name: str, method: str,
                      req_params: Optional[dict] = None,
                      req_body: Optional[dict] = None,
                      proxies: Optional[dict] = None,
                      **kwargs) -> ResponseResult:
        """
        :param access_token:
        :param route_name: 请求路径
        :param method: GET/POST/PUT,etc
        :param req_params: query参数放这里, 没有则不传
        :param req_body: 请求体参数放这里, 没有则不传
        :param proxies: 代理字典，例如 {"http": "http://user:pass@host:port", "https": "http://user:pass@host:port"}；默认使用构造函数传入的全局代理
        :param kwargs: timeout、ssl、debug 等其他字段可以放这里
        :return:
        """
        req_url = self.host + route_name
        headers = kwargs.pop('headers', {})

        req_params = req_params or {}
        gen_sign_params = copy.deepcopy(req_body) if req_body else {}
        if req_params:
            gen_sign_params.update(req_params)

        sign_params = {
            "app_key": self.app_id,
            "access_token": access_token,
            "timestamp": f'{int(time.time())}',
        }
        gen_sign_params.update(sign_params)
        sign = SignBase.generate_sign(self.app_id, gen_sign_params)
        sign_params["sign"] = sign
        req_params.update(sign_params)

        # 对于带有请求体的, 需要设置默认的Content-Type
        if req_body and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        effective_proxies = self.proxies if proxies is None else proxies
        return await HttpBase().request(method, req_url, params=req_params,
                                        headers=headers, json=req_body, proxies=effective_proxies, **kwargs)
