"""统一 DRF 响应与异常处理工具。

模块说明：为项目提供一致的 API 返回格式与异常到响应的转换。

主要导出：
- `drf_ok`：统一成功响应格式
- `drf_error`：统一错误响应格式
- `BizError`：用于在业务层抛出可被统一转换的异常
- `custom_exception_handler`：DRF 的自定义异常处理器
"""

from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import (
    APIException,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    ValidationError,
    AuthenticationFailed,
)

SUCCESS_CODE = "00000"
PARAM_ERROR_CODE = "B0001"
AUTH_ERROR_CODE = "A0201"  # 未登录
PERMISSION_DENIED_CODE = "A0301"  # 无权限
NOT_FOUND_CODE = "A0404"  # 资源不存在
SERVER_ERROR_CODE = "B0500"  # 服务器内部错误

def drf_ok(data=None, msg: str = "success", status: int = 200) -> Response:
    """构造统一的成功响应。

    规范：{"code": SUCCESS_CODE, "data": ..., "msg": ...}

    注：当 `status==204` 时返回空响应以避免代理/浏览器对 Content-Length 的异常处理。
    """
    if status == 204:
        return Response(status=status)
    return Response({"code": SUCCESS_CODE, "data": data, "msg": msg}, status=status)


def drf_error(msg: str = "error", code: str = PARAM_ERROR_CODE, status: int = 400, data=None) -> Response:
    """构造统一错误响应。

    返回结构同 `drf_ok`，但 `code` 表示业务错误码。
    """
    return Response({"code": code, "data": data, "msg": msg}, status=status)


class BizError(Exception):
    """业务层可抛出的异常，最终会被 `custom_exception_handler` 转换为统一响应。"""

    def __init__(self, msg: str, code: str = PARAM_ERROR_CODE, status: int = 400, data=None):
        super().__init__(msg)
        self.msg = msg
        self.code = code
        self.status = status
        self.data = data


def exception_to_response(exc: Exception) -> Response:
    """将任意异常转换为 `Response`。

    - `BizError` 会保留其业务码与状态
    - 其它未知异常映射为 500
    """
    if isinstance(exc, BizError):
        return drf_error(exc.msg, code=exc.code, status=exc.status, data=exc.data)
    return drf_error("服务器内部错误", code=SERVER_ERROR_CODE, status=500)


def custom_exception_handler(exc, context):
    """DRF 自定义异常处理入口。

    将 DRF 与业务异常映射为统一的 JSON 响应结构，便于前端解析与展示。
    """
    if isinstance(exc, BizError):
        return exception_to_response(exc)

    response = drf_exception_handler(exc, context)
    if response is not None:
        status = response.status_code
        if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            code = AUTH_ERROR_CODE
            msg = str(getattr(exc, 'detail', '未登录'))
        elif isinstance(exc, PermissionDenied):
            code = PERMISSION_DENIED_CODE
            msg = str(getattr(exc, 'detail', '无权限'))
        elif isinstance(exc, NotFound):
            code = NOT_FOUND_CODE
            msg = str(getattr(exc, 'detail', '资源不存在'))
        elif isinstance(exc, ValidationError):
            code = PARAM_ERROR_CODE
            detail = getattr(exc, 'detail', None)
            msg = '参数错误'
            data = detail
            return drf_error(msg=msg, code=code, status=status, data=data)
        else:
            code = SERVER_ERROR_CODE
            msg = str(getattr(exc, 'detail', '服务器错误'))
        return drf_error(msg=msg, code=code, status=status, data=response.data)

    return exception_to_response(exc)
