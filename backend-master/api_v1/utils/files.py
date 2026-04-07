"""文件管理占位模块。

模块说明：当前项目将文件上传功能下线，保留此模块作为兼容层，所有上传请求返回 HTTP 410。
"""
from api_v1.utils.responses import drf_error


def save_uploaded(file_obj, user=None):  # pragma: no cover
    """占位上传函数，始终返回 410 错误响应。

    返回 (None, Response) 以兼容原先调用方的返回约定。
    """
    return None, drf_error("文件管理已禁用", status=410)
