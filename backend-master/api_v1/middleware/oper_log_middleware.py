"""操作日志中间件。

记录 ``/api/v1/`` 下接口请求到 :class:`OperLog`：
- module: 路径首段（users / roles 等）
- action: HTTP method
- operator: 用户名（匿名为空）
- ip / user_agent / elapsed_ms / result

注意：当前未在 ``settings.MIDDLEWARE`` 中注册（已废弃），保留供后续按需启用。
"""
from __future__ import annotations

import time

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from api_v1.models import OperLog


class OperLogMiddleware(MiddlewareMixin):
    """请求耗时与结果落库中间件。

    低风险实现：写日志失败不影响主流程；后续可扩展批量写入与异常栈采集。
    """

    def process_request(self, request: HttpRequest):
        request._oplog_start = time.time()
        return None

    def process_response(self, request: HttpRequest, response: HttpResponse):
        try:
            path = request.path
            if not path.startswith("/api/v1/"):
                return response
            segs = [s for s in path[len("/api/v1/"):].split("/") if s]
            module = segs[0] if segs else "root"
            action = request.method.lower()
            user = getattr(request, "user", None)
            operator = user.username if user and getattr(user, "is_authenticated", False) else ""
            ip = request.META.get("REMOTE_ADDR", "")
            ua = request.META.get("HTTP_USER_AGENT", "")[:255]
            elapsed_ms = int((time.time() - getattr(request, "_oplog_start", time.time())) * 1000)
            OperLog.objects.create(
                module=module,
                action=action,
                operator=operator,
                ip=ip,
                user_agent=ua,
                result="success" if 200 <= response.status_code < 400 else "error",
                elapsed_ms=elapsed_ms,
            )
        except Exception:
            # 不影响主流程
            pass
        return response

    def process_exception(self, request: HttpRequest, exception: Exception):
        try:
            path = request.path
            if not path.startswith("/api/v1/"):
                return None
            segs = [s for s in path[len("/api/v1/"):].split("/") if s]
            module = segs[0] if segs else "root"
            action = request.method.lower()
            user = getattr(request, "user", None)
            operator = user.username if user and getattr(user, "is_authenticated", False) else ""
            ip = request.META.get("REMOTE_ADDR", "")
            ua = request.META.get("HTTP_USER_AGENT", "")[:255]
            elapsed_ms = int((time.time() - getattr(request, "_oplog_start", time.time())) * 1000)
            OperLog.objects.create(
                module=module,
                action=action,
                operator=operator,
                ip=ip,
                user_agent=ua,
                result="error",
                elapsed_ms=elapsed_ms,
            )
        except Exception:
            pass
        return None
