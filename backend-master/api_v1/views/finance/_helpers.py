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
import threading


try:
    from api_v1.models import OrderProfitCache
except Exception:
    OrderProfitCache = None


# 辅助工具移动到模块级以保持 `download` 函数简洁
def parse_months(r: str):
    try:
        if isinstance(r, str) and '-' in r:
            a, b = r.split('-', 1)
            def to_ym(x):
                y = int(x[:4]); m = int(x[4:6]); return y, m
            ys, ms = to_ym(a); ye, me = to_ym(b)
            months = []
            y, m = ys, ms
            while (y < ye) or (y == ye and m <= me):
                months.append(f"{y:04d}-{m:02d}")
                m += 1
                if m > 12:
                    m = 1; y += 1
            return months
        return []
    except Exception:
        return []


def parse_store_param(store_param):
    stores = []
    if not store_param:
        return stores
    try:
        if isinstance(store_param, str):
            try:
                parsed = json.loads(store_param)
                if isinstance(parsed, list):
                    stores = [str(x).strip() for x in parsed if x is not None and str(x).strip()]
                else:
                    stores = [s.strip() for s in store_param.split(',') if s.strip()]
            except Exception:
                stores = [s.strip() for s in store_param.split(',') if s.strip()]
        elif isinstance(store_param, (list, tuple, set)):
            stores = [str(x).strip() for x in store_param if x is not None and str(x).strip()]
        else:
            stores = [str(store_param).strip()]
    except Exception:
        stores = []
    return stores


def _safe_float(x):
    try:
        if x is None or (isinstance(x, str) and str(x).strip() == ''):
            return None
        return float(x)
    except Exception:
        try:
            return float(str(x).strip())
        except Exception:
            return None


def _safe_int(x):
    try:
        if x is None or (isinstance(x, str) and str(x).strip() == ''):
            return None
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return None


def _agg_sum(a, b):
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return a + b


def _agg_int_sum(a, b):
    s = _agg_sum(a, b)
    if s is None:
        return None
    try:
        return int(s)
    except Exception:
        try:
            return int(float(s))
        except Exception:
            return None


def norm_month(x):
    try:
        if x is None:
            return None
        s = str(x).strip()
        if re.match(r'^\d{6}$', s):
            return f"{s[:4]}-{s[4:6]}"
        return s
    except Exception:
        return None


RATIO_FIELDS = {'gross_margin', 'net_gross_margin', 'return_rate', 'refund_amount_rate', 'spend_rate'}


def format_ratio_value(v):
    if v is None or v == '':
        return ''
    try:
        fv = float(v)
        if abs(fv) <= 1:
            fv = fv * 100.0
        return f"{fv:.2f}%"
    except Exception:
        return str(v)


def determine_month_color(month_vals):
    try:
        gp = month_vals.get('gross_profit')
        refund = month_vals.get('refund_amount_rate')
        ad_rate = month_vals.get('spend_rate')

        def _norm_pct(v):
            try:
                if v is None:
                    return None
                fv = float(v)
                if abs(fv) <= 1:
                    return fv * 100.0
                return fv
            except Exception:
                return None

        gp_v = None
        try:
            gp_v = float(gp) if gp is not None else None
        except Exception:
            gp_v = None
        refund_v = _norm_pct(refund)
        ad_v = _norm_pct(ad_rate)
        # 规则判断：均要求毛利润 < 0
        if gp_v is not None and gp_v < 0:
            if refund_v is not None and ad_v is not None and refund_v > 15 and ad_v > 10:
                return 'FFFF0000'  # red
            if refund_v is not None and refund_v > 15 and (ad_v is None or ad_v <= 10):
                return 'FF00AA00'  # green
            if refund_v is not None and refund_v <= 15 and ad_v is not None and ad_v > 10:
                return 'FFFFFF00'  # yellow
        return None
    except Exception:
        return None


# 模块级辅助函数：缓存与响应处理（从 download 中抽取，便于复用和单元测试）
def build_cache_key(owner_q, time_range, stores, months, batch_size):
    try:
        cache_input = {
            'owner': owner_q,
            'time': time_range,
            'stores': stores,
            'months': months,
            'batch_size': batch_size,
        }
        cache_raw = json.dumps(cache_input, ensure_ascii=False, sort_keys=True)
        return 'monthly_loss_xlsx_' + hashlib.sha256(cache_raw.encode('utf-8')).hexdigest()
    except Exception:
        return None


def is_refresh_requested(payload) -> bool:
    try:
        for rf_key in ('refresh', 'refresh_cache', 'force_refresh'):
            v = payload.get(rf_key)
            if isinstance(v, str):
                if v.strip().lower() in ('1', 'true', 'yes', 'y', 'on'):
                    return True
            elif v:
                return True
    except Exception:
        pass
    return False


def try_get_cached_file_response(cache_key, months):
    try:
        if not cache_key:
            return None
        cached = cache.get(cache_key)
        if not cached:
            return None
        # dict with 'data'
        if isinstance(cached, dict) and cached.get('data'):
            data_bytes = cached.get('data')
            filename = cached.get('filename') or f"monthly_loss_{months[0].replace('-','')}_{months[-1].replace('-','')}.xlsx"
            bio = io.BytesIO(data_bytes)
            from django.http import FileResponse
            resp = FileResponse(bio, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f'attachment; filename="{filename}"'
            return resp
        # dict with 'path'
        if isinstance(cached, dict) and cached.get('path'):
            p = cached.get('path')
            try:
                if p and os.path.exists(p):
                    f = open(p, 'rb')
                    from django.http import FileResponse
                    resp = FileResponse(f, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    resp['Content-Disposition'] = f'attachment; filename="{cached.get("filename") or os.path.basename(p)}"'
                    return resp
            except Exception:
                return None
        # raw bytes
        if isinstance(cached, (bytes, bytearray)):
            bio = io.BytesIO(bytes(cached))
            from django.http import FileResponse
            resp = FileResponse(bio, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f'attachment; filename="monthly_loss_{months[0].replace('-','')}_{months[-1].replace('-','')}.xlsx"'
            return resp
    except Exception:
        return None
    return None


def remove_cache_and_disk(cache_key):
    try:
        if not cache_key:
            return
        old = None
        try:
            old = cache.get(cache_key)
        except Exception:
            old = None
        try:
            cache.delete(cache_key)
        except Exception:
            pass
        try:
            if isinstance(old, dict) and old.get('path'):
                pth = old.get('path')
                try:
                    if pth and os.path.exists(pth):
                        os.remove(pth)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            media_root = getattr(settings, 'MEDIA_ROOT', None) or os.path.join(os.path.dirname(__file__), '..', 'media')
            export_dir = os.path.join(media_root, 'export_cache')
            file_path = os.path.join(export_dir, f"{cache_key}.xlsx")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        except Exception:
            pass
    except Exception:
        pass


def cache_data_bytes_with_fallback(cache_key, data_bytes, filename):
    try:
        if not cache_key or data_bytes is None:
            return False
        try:
            ok = cache.set(cache_key, {'data': data_bytes, 'filename': filename}, timeout=None)
        except TypeError:
            ok = cache.set(cache_key, {'data': data_bytes, 'filename': filename})
        # 某些缓存后端（Django core/backends）返回 None 表示成功，仅当明确返回 False 时视为失败
        if ok is not False:
            return True
        # 回退到磁盘
        try:
            media_root = getattr(settings, 'MEDIA_ROOT', None) or os.path.join(os.path.dirname(__file__), '..', 'media')
            export_dir = os.path.join(media_root, 'export_cache')
            os.makedirs(export_dir, exist_ok=True)
            file_path = os.path.join(export_dir, f"{cache_key}.xlsx")
            with open(file_path, 'wb') as wf:
                wf.write(data_bytes)
            try:
                cache.set(cache_key, {'path': file_path, 'filename': filename}, timeout=None)
            except TypeError:
                cache.set(cache_key, {'path': file_path, 'filename': filename})
            return True
        except Exception:
            # 写磁盘回退失败则继续由外层捕获并返回 False
            pass
        return False
    except Exception:
        return False


def stream_tempfile_response(tmp_name, filename, delay=30):
    try:
        from django.http import FileResponse
        f = open(tmp_name, 'rb')
        resp = FileResponse(f, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'

        def _cleanup_file(path_file, delay_sec=delay):
            try:
                time.sleep(delay_sec)
                try:
                    os.remove(path_file)
                except Exception:
                    pass
            except Exception:
                pass

        t = threading.Thread(target=_cleanup_file, args=(tmp_name,))
        t.daemon = True
        t.start()
        return resp
    except Exception:
        return None

