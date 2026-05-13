"""api_v1 认证后端包。

按"一类一文件"规则拆分各认证类。``settings.REST_FRAMEWORK`` 中
``DEFAULT_AUTHENTICATION_CLASSES`` 引用路径 ``api_v1.auth.BearerTokenAuthentication``
通过本 ``__init__`` 重导出保持兼容。
"""
from api_v1.auth.bearer_token_auth import BearerTokenAuthentication

__all__ = ["BearerTokenAuthentication"]
