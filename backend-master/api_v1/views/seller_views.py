import traceback
import time
from typing import List

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.utils.responses import drf_ok, drf_error
# write_log 调用已移除
from django.conf import settings
from concurrent.futures import TimeoutError as FuturesTimeout

try:
    from openapi.client import LingXingClient
except Exception:
    LingXingClient = None


class SellerViewSet(viewsets.ViewSet):
    """通过 LingXing OpenAPI 获取授权店铺列表并返回给前端"""

    def get_permissions(self):
        # GET 列表接口允许匿名访问以便前端取下拉；如需鉴权请改为 IsAuthenticated
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        if method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        t0 = time.perf_counter()
        try:
            if LingXingClient is None:
                return drf_error('LingXing client not available', status=500)
                
            client = LingXingClient()
            # 将前端的 query string 透传给上游（如有）
            params = dict(request.GET.items())
            try:
                resp = client.request_sync('/erp/sc/data/seller/lists', 'GET', req_params=params, timeout=30)
            except FuturesTimeout:
                tb = traceback.format_exc()
                # logging removed: 获取店铺下拉失败(timeout)
                return drf_error('获取 LingXing access_token 超时', status=504, data={'msg': 'access_token timeout', 'trace': tb})
            except Exception as e:
                tb = traceback.format_exc()
                # logging removed: 获取店铺下拉失败(request)
                return drf_error('调用 LingXing 接口失败', status=502, data={'msg': str(e), 'trace': tb})

            # resp 应为 openapi.resp_schema.ResponseResult
            if not resp:
                return drf_error('empty response from lingxing', status=502)

            # 根据 LingXing 返回的业务 code 判断成功（文档中 code==0 表示成功）
            try:
                code = int(getattr(resp, 'code', -1) or -1)
            except Exception:
                code = -1

            if code != 0:
                # 如果上游返回 code != 0，但带有可用的 data（兼容一些异常场景），记录为警告并尝试继续处理
                data_candidate = getattr(resp, 'data', None)
                if isinstance(data_candidate, list) and len(data_candidate) > 0:
                    # logging removed: 上游返回非0 code 但包含数据，降级继续
                    data = data_candidate
                else:
                    # 包装上游错误信息
                    return drf_error(msg=f"remote error: {getattr(resp, 'message', '')}", status=502, data={'remote': resp.dict() if hasattr(resp, 'dict') else resp})
            else:
                data = getattr(resp, 'data', []) or []
            out: List[dict] = []
            for item in data:
                try:
                    sid = item.get('sid') or item.get('id') or item.get('shop_id')
                    name = item.get('name') or item.get('shop') or ''
                    country = item.get('country') or ''
                    out.append({
                        'id': sid,
                        'name': name,
                        'country': country,
                        # 兼容前端展示：前端可取 label/name 与 country separately
                        'label': name,
                        'label_extra': country,
                        # 保留原始条目以便前端需要其他字段
                        'raw': item,
                    })
                except Exception:
                    continue

            # logging removed: 获取店铺下拉
            return drf_ok(out)

        except Exception as e:
            tb = traceback.format_exc()
            # logging removed: 获取店铺下拉失败
            return drf_error('获取店铺数据失败', status=500, data={'msg': str(e), 'trace': tb})

    @action(detail=False, methods=["get"], url_path="owners")
    def owners(self, request):
        """通过 LingXing OpenAPI 获取账号列表，筛选 status==1，返回 realname 作为负责人下拉选项"""
        t0 = time.perf_counter()
        try:
            if LingXingClient is None:
                return drf_error('LingXing client not available', status=500)

            client = LingXingClient()
            params = dict(request.GET.items())
            try:
                resp = client.request_sync('/erp/sc/data/account/lists', 'GET', req_params=params, timeout=30)
            except FuturesTimeout:
                tb = traceback.format_exc()
                # logging removed: 获取负责人下拉失败(timeout)
                return drf_error('获取 LingXing access_token 超时', status=504, data={'msg': 'access_token timeout', 'trace': tb})
            except Exception as e:
                tb = traceback.format_exc()
                # logging removed: 获取负责人下拉失败(request)
                return drf_error('调用 LingXing 接口失败', status=502, data={'msg': str(e), 'trace': tb})

            if not resp:
                return drf_error('empty response from lingxing', status=502)

            try:
                code = int(getattr(resp, 'code', -1) or -1)
            except Exception:
                code = -1

            # 如果上游返回非0但包含数据列表，降级继续；否则视为错误
            if code != 0:
                data_candidate = getattr(resp, 'data', None)
                if isinstance(data_candidate, list) and len(data_candidate) > 0:
                    # logging removed: 上游返回非0 code 但包含负责人数据，降级继续
                    data = data_candidate
                else:
                    return drf_error(msg=f"remote error: {getattr(resp, 'message', '')}", status=502, data={'remote': resp.dict() if hasattr(resp, 'dict') else resp})
            else:
                data = getattr(resp, 'data', []) or []

            out: List[dict] = []
            for it in data:
                try:
                    status = int(it.get('status', 0) or 0)
                    if status != 1:
                        continue
                    uid = it.get('uid') or it.get('id')
                    realname = it.get('realname') or it.get('name') or it.get('username') or ''
                    out.append({'id': uid, 'label': realname, 'name': realname, 'raw': it})
                except Exception:
                    continue

            # logging removed: 获取负责人下拉
            return drf_ok(out)


        except Exception as e:
            tb = traceback.format_exc()
            # logging removed: 获取负责人下拉失败
            return drf_error('获取负责人数据失败', status=500, data={'msg': str(e), 'trace': tb})
