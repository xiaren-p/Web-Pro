import traceback
from typing import List, Optional
import json
import re
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
import io
import os
import time
import tempfile
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.utils.responses import drf_ok, drf_error
from api_v1.utils.pagination import paginate_queryset
from api_v1.models import MonthlyLossOrder, MonthlyLossOrderFirst20
from api_v1.serializers import MonthlyLossSerializer, MonthlyLossFirst20Serializer
from django.core.cache import cache


try:
    from api_v1.models import OrderProfitCache
except Exception:
    OrderProfitCache = None

from api_v1.views.finance._helpers import (parse_months, parse_store_param, _safe_float, _safe_int, _agg_sum, _agg_int_sum, norm_month, RATIO_FIELDS, format_ratio_value, determine_month_color, build_cache_key, is_refresh_requested, try_get_cached_file_response, remove_cache_and_disk, cache_data_bytes_with_fallback, stream_tempfile_response)

class StatisticsViewSet(viewsets.ViewSet):
    """统计类接口（包括 lossmaking orders 查询）"""

    def get_permissions(self):
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        if method in ('GET', 'POST'):
            return [AllowAny()]
        return [IsAuthenticated()]

    # 模块级辅助函数：供多个 endpoint 和后台刷新的线程复用
    @staticmethod
    def parse_number(v) -> Optional[float]:
        """
        将各种可能的数值表示安全地解析为 float。

        支持输入类型：int、float、带千分位逗号的字符串（例如 "1,234.56"）、空字符串或 None。
        解析规则：
        - 若输入为 None 或空字符串，返回 None；
        - 若输入为 int/float，返回对应的 float 值；
        - 若输入为字符串，则移除逗号并尝试转换为 float，转换失败返回 None。

        该函数用于解析上游接口返回的可能为字符串的数值字段（例如 `gross_margin`），
        并在遇到异常数据时避免抛出异常影响整体流程。

        :param v: 待解析的值
        :return: 解析后的 float，或解析失败时的 None
        """
        try:
            if v is None:
                return None
            if isinstance(v, (int, float)):
                return float(v)
            s = str(v).replace(',', '').strip()
            if s == '':
                return None
            return float(s)
        except Exception:
            return None

    @staticmethod
    def pick_fields(item: dict) -> dict:
        """
        从上游单条记录中抽取并规范化需要缓存和返回给前端的字段集合。

        目的：减少缓存体积，隔离上游字段变动对前端的影响，同时只保留前端关心的字段。

        返回字段示例：`gross_margin`, `gross_profit`, `currency_icon`, `sids`, `price_list`,
        `seller_store_countries`（只保留国家名），以及局部的 `local_infos`（只保留 name/sku）。

        :param item: 上游返回的单条记录
        :return: 仅包含必要字段的字典
        """
        return {
            'gross_margin': item.get('gross_margin'),
            'gross_profit': item.get('gross_profit'),
            'currency_icon': item.get('currency_icon'),
            'principal_names': item.get('principal_names'),
            'sids': item.get('sids'),
            'small_image_url': item.get('small_image_url'),
            'currency_code': item.get('currency_code'),
            'price_list': item.get('price_list') or [],
            'parent_asins': item.get('parent_asins') or [],
            'seller_store_countries': [c.get('name') for c in (item.get('seller_store_countries') or []) if c.get('name')],
            'local_infos': [
                {'local_name': li.get('local_name'), 'local_sku': li.get('local_sku')} for li in (item.get('local_infos') or [])
            ],
            'net_gross_margin': item.get('net_gross_margin'),
            'return_rate': item.get('return_rate'),
            'refund_amount_rate': item.get('refund_amount_rate'),
            'total_stock_fee': item.get('total_stock_fee'),
            'spend': item.get('spend'),
            'spend_rate': item.get('spend_rate'),
        }


    def apply_rule(self, items: List[dict], rule_name: Optional[str]) -> List[dict]:
        """
        根据传入的 `rule_name` 对 items 做规则化处理或过滤。

        说明：当前方法为占位实现（no-op），保留多个 rule 分支以便未来扩展具体规则逻辑。
        如果没有提供 `rule_name` 或遇到异常，会直接返回原始 items。

        :param items: 待处理的条目列表（通常为 pick_fields 之后的条目）
        :param rule_name: 规则名称（字符串），例如 'rule1' 等
        :return: 经规则处理后的条目列表
        """
        if not rule_name:
            return items
        out: List[dict] = []
        for it in items:
            try:
                gm = self.parse_number(it.get('gross_profit'))
                refund = self.parse_number(it.get('refund_amount_rate'))
                spend = self.parse_number(it.get('spend_rate'))
                cond1 = (gm is not None and gm < 0)
                cond2 = (refund is not None and refund > 0.15)
                cond3 = (spend is not None and spend > 0.10)
                match = False
                if rule_name == 'rule1':
                    match = cond1 or cond2 or cond3
                elif rule_name == 'rule2':
                    match = cond1 and cond2 and cond3
                elif rule_name == 'rule3':
                    match = cond1 and cond2 and not cond3
                elif rule_name == 'rule4':
                    match = cond1 and cond3 and not cond2
                if match:
                    out.append(it)
            except Exception:
                # 单条解析异常跳过
                continue
        return out

    @action(detail=False, methods=["post"], url_path="lossmakingorders_sync")
    def lossmaking_orders_sync(self, request):
        """返回本次查询应使用的缓存 key 与上次同步时间，并告知是否需要刷新缓存。

        请求 body (JSON): 同 `lossmakingorders`（sids/startDate/endDate/currencyCode/rule）
        返回: { key: str, sync_time: str|null, needs_refresh: bool }
        """
        # 说明：该接口只负责判断与触发后台刷新（若需要），不直接返回业务数据。
        # 返回字段解释：
        # - key: 本次查询对应的缓存 key，供前端后续调用 `lossmakingorders_data` 使用；
        # - sync_time: 上次缓存写入时间（ISO 格式），若无缓存则为 null；
        # - needs_refresh: 若缓存不存在或超过 10 分钟则为 True；若最近已刷新则为 False；
        # - syncing: 如果本次触发了后台刷新或已有其他进程在刷新，则为 True（表示正在同步）。
        try:
            if getattr(request, 'method', '').upper() == 'GET':
                payload = request.query_params or {}
            else:
                payload = request.data or {}

            # sids 解析块已移除（不再需要）

            start_date = payload.get('startDate')
            end_date = payload.get('endDate')
            if not (start_date and end_date):
                return drf_error('startDate and endDate are required', status=400)

            currency_code = payload.get('currencyCode')

            try:
                key_obj = {
                    'startDate': start_date,
                    'endDate': end_date,
                    'currencyCode': currency_code,
                }
                key_raw = json.dumps(key_obj, ensure_ascii=False, sort_keys=True)
                cache_key = hashlib.sha256(key_raw.encode('utf-8')).hexdigest()
            except Exception:
                return drf_error('failed to build cache key', status=500)

            cache_created_at = None
            needs_refresh = True
            try:
                if cache_key and OrderProfitCache is not None:
                    entry = OrderProfitCache.objects.filter(key=cache_key).first()
                    if entry:
                        try:
                            # 使用 updated_at 判断缓存是否过期（update_or_create 会刷新 updated_at）
                            cache_created_at = entry.updated_at.isoformat()
                            if timezone.now() - entry.updated_at <= timedelta(minutes=10):
                                needs_refresh = False
                        except Exception:
                            pass
            except Exception:
                pass

            # 上游同步能力已移除，syncing 始终为 false
            syncing_flag = False

            return drf_ok({'key': cache_key, 'sync_time': cache_created_at, 'needs_refresh': needs_refresh, 'syncing': syncing_flag})
        except Exception as e:
            tb = traceback.format_exc()
            return drf_error('lossmakingorders_sync failed', status=500, data={'msg': str(e), 'trace': tb})


    @action(detail=False, methods=["post"], url_path="lossmakingorders_data")
    def lossmaking_orders_data(self, request):
        """根据 cache key 返回缓存的 pick_fields 数据。
        请求 body (JSON): { key: str, page?: int, page_size?: int }
        返回: { list: [...], total: int, sync_time: str|null }
        """
        # 说明：该接口仅从 `OrderProfitCache` 读取已缓存的 `pick_fields` 数据并按页返回，
        # 不会触发上游请求或对数据做额外过滤（前端若需过滤可在客户端完成或调用其它接口）。
        try:
            if getattr(request, 'method', '').upper() == 'GET':
                payload = request.query_params or {}
            else:
                payload = request.data or {}

            cache_key = payload.get('key')
            if not cache_key:
                return drf_error('key is required', status=400)

            page = int(payload.get('page', 1) or 1)
            page_size = int(payload.get('page_size', 50) or 50)

            data_list = []
            sync_time = None
            try:
                if OrderProfitCache is not None:
                    entry = OrderProfitCache.objects.filter(key=cache_key).first()
                    if entry:
                        try:
                            data_list = json.loads(entry.data or '[]')
                        except Exception:
                            data_list = []
                        try:
                            # 返回最近一次写入时间，使用 updated_at
                            sync_time = entry.updated_at.isoformat()
                        except Exception:
                            sync_time = None
            except Exception:
                data_list = []
            # 额外支持基于 listing 负责人（owners）、MSKU（searchValue）和 rule 的服务器端筛选。
            # 解析可选筛选参数（兼容字符串或数组）
            owners = payload.get('owners')
            if isinstance(owners, str):
                try:
                    owners = json.loads(owners)
                except Exception:
                    owners = [x.strip() for x in owners.split(',') if x.strip()]

            search_value = payload.get('searchValue') or payload.get('msku')
            if isinstance(search_value, str):
                # 支持多行输入
                search_value = [s.strip() for s in search_value.splitlines() if s.strip()]

            # 可选的 sids 过滤：前端在 data 阶段可传入 sids 列表用于基于 item.sids 做服务器端过滤
            sids_filter = payload.get('sids')
            if isinstance(sids_filter, str):
                try:
                    sids_filter = json.loads(sids_filter)
                except Exception:
                    try:
                        sids_filter = [int(x) for x in sids_filter.split(',') if x.strip()]
                    except Exception:
                        sids_filter = [x.strip() for x in sids_filter.split(',') if x.strip()]

            rule_name = payload.get('rule') or None

            # 支持排序参数：sort_by 和 sort_order（'asc' / 'desc'）
            sort_by = payload.get('sort_by')
            sort_order = (payload.get('sort_order') or 'asc').lower()

            def match_owners(item: dict, owners_list) -> bool:
                if not owners_list:
                    return True
                principals = []
                # 首选从 price_list 中提取 principal_uids（可能为 list、单值或分隔字符串）
                for p in (item.get('price_list') or []):
                    try:
                        if not isinstance(p, dict):
                            continue
                        u = None
                        if 'principal_uids' in p:
                            u = p.get('principal_uids')
                        elif 'principal_uid' in p:
                            u = p.get('principal_uid')
                        else:
                            # 兼容不同大小写或命名的字段
                            for k in p.keys():
                                if k.lower() in ('principal_uid', 'principaluids', 'principal_uids', 'principaluid'):
                                    u = p.get(k)
                                    break
                        if u is None:
                            continue
                        if isinstance(u, list):
                            for x in u:
                                if x is not None:
                                    principals.append(str(x).strip())
                        else:
                            # 可能为带分隔符的字符串或单一值
                            us = str(u)
                            if re.search(r'[,;\n]', us):
                                principals.extend([s.strip() for s in re.split(r'[,\n;]+', us) if s.strip()])
                            else:
                                if us.strip():
                                    principals.append(us.strip())
                    except Exception:
                        continue

                # 将 owners_list 中的任意项与 principals 精确比较（字符串化后比对）
                for o in owners_list:
                    for p in principals:
                        if str(o).strip() == str(p).strip():
                            return True
                return False

            def match_msku(item: dict, msku_list) -> bool:
                if not msku_list:
                    return True
                # 从 price_list/local_infos 中提取可能的 MSKU 值进行匹配
                candidates = []
                for p in (item.get('price_list') or []):
                    try:
                        if isinstance(p, dict):
                            if p.get('local_sku'):
                                candidates.append(str(p.get('local_sku')))
                            if p.get('sku'):
                                candidates.append(str(p.get('sku')))
                    except Exception:
                        continue
                for li in (item.get('local_infos') or []):
                    try:
                        if isinstance(li, dict) and li.get('local_sku'):
                            candidates.append(str(li.get('local_sku')))
                    except Exception:
                        continue
                # 精确匹配任意一项
                for q in msku_list:
                    for c in candidates:
                        if str(q).strip() == str(c).strip():
                            return True
                return False

            def match_sids(item: dict, sids_list) -> bool:
                if not sids_list:
                    return True
                item_sids = item.get('sids') or []
                vals = []
                try:
                    if isinstance(item_sids, str):
                        vals = [s.strip() for s in re.split(r'[,;\n]+', item_sids) if s.strip()]
                    elif isinstance(item_sids, list):
                        vals = [str(x).strip() for x in item_sids if x is not None]
                    else:
                        vals = [str(item_sids).strip()]
                except Exception:
                    vals = [str(item_sids)]
                for q in sids_list:
                    for v in vals:
                        if str(q).strip() == str(v).strip():
                            return True
                return False

            # 应用 owners / MSKU 过滤
            try:
                filtered = []
                for it in data_list:
                    if not match_owners(it, owners):
                        continue
                    if not match_msku(it, search_value):
                        continue
                    if not match_sids(it, sids_filter):
                        continue
                    filtered.append(it)
            except Exception:
                filtered = data_list

            # 应用规则过滤（由 apply_rule 处理，当前为占位实现）
            try:
                filtered = self.apply_rule(filtered, rule_name)
            except Exception:
                pass

            # 应用排序（服务器端）
            try:
                if sort_by:
                    allowed = {'gross_profit', 'gross_margin', 'net_gross_margin', 'return_rate', 'refund_amount_rate', 'total_stock_fee', 'spend', 'spend_rate'}
                    if str(sort_by) in allowed:
                        # 为了保证 None 值始终排在末尾，按不同排序方向构造 key
                        if str(sort_order) == 'desc':
                            def sort_key(it):
                                v = it.get(sort_by)
                                n = self.parse_number(v)
                                if n is None:
                                    return (1, 0)
                                return (0, -n)
                        else:
                            def sort_key(it):
                                v = it.get(sort_by)
                                n = self.parse_number(v)
                                if n is None:
                                    return (1, 0)
                                return (0, n)
                        try:
                            filtered.sort(key=sort_key)
                        except Exception:
                            pass
            except Exception:
                pass

            total = len(filtered)
            start_idx = max(0, (page - 1) * page_size)
            end_idx = start_idx + page_size
            page_items = filtered[start_idx:end_idx]

            return drf_ok({'list': page_items, 'total': total, 'sync_time': sync_time})
        except Exception as e:
            tb = traceback.format_exc()
            return drf_error('lossmakingorders_data failed', status=500, data={'msg': str(e), 'trace': tb})


