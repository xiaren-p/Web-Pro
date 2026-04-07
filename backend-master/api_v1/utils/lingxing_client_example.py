"""
示例：如何在 Django 视图或业务逻辑中使用 LingXingClient。

同步视图示例：
    from api_v1.utils.lingxing_client_example import example_sync_usage
    result = example_sync_usage()

异步（如果你的视图是 async）示例：可以直接使用 openapi.token_manager.TokenManager
"""
from openapi.client import LingXingClient


def example_sync_usage():
    """同步示例：自动获取 access_token 并发起 GET 请求。返回 openapi.resp_schema.ResponseResult 对象。"""
    client = LingXingClient()
    # 例如请求：GET /api/example
    resp = client.request_sync("/api/example", "GET", req_params={})
    return resp


async def example_async_usage():
    from openapi.token_manager import TokenManager
    # 异步示例：直接使用 TokenManager
    tm = await TokenManager.get_instance(host=None)
    token = await tm.get_access_token()
    from openapi.openapi import OpenApiBase
    api = OpenApiBase(host=None, app_id=None, app_secret=None)
    return await api.request(token, "/api/example", "GET")
