import traceback
import threading
from typing import List, Optional
import json
import re
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import io
import os
import time
import tempfile
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.common.utils.responses import drf_ok, drf_error
from apps.common.utils.pagination import paginate_queryset
from apps.finance.models.monthly_loss_order import MonthlyLossOrder
from apps.finance.models.monthly_loss_order_first20 import MonthlyLossOrderFirst20


def parse_months(r):
    """将月份范围字符串展开为连续月份列表。

    支持形如 ``"202501-202503"`` 的范围输入，返回 ``["2025-01", "2025-02", "2025-03"]``。
    若输入不含 ``-`` 或解析失败则返回空列表。

    Args:
        r (str): 月份范围字符串，格式 ``YYYYMM-YYYYMM``。

    Returns:
        list[str]: 连续月份列表，格式 ``YYYY-MM``；解析失败返回 ``[]``。
    """
    try:
        if isinstance(r, str) and '-' in r:
            a, b = r.split('-', 1)
            def to_ym(x):
                """将 ``YYYYMM`` 字符串转换为 ``(year, month)`` 元组。"""
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
    """解析店铺筛选参数，统一返回店铺 ID 列表。

    支持多种输入类型：JSON 字符串 ``"[1,2,3]"``、逗号分隔字符串 ``"1,2,3"``、
    列表/元组 ``[1, 2, 3]``。空值返回空列表。

    Args:
        store_param (str | list | tuple | set | None): 原始店铺参数。

    Returns:
        list[str]: 去空后的店铺 ID 字符串列表。
    """
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
    """安全转换为浮点数，无法转换时返回 ``None``。

    Args:
        x: 任意输入值（str / int / float / None）。

    Returns:
        float | None: 转换后的浮点数；空值或异常返回 ``None``。
    """
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
    """安全转换为整数，无法转换时返回 ``None``。

    Args:
        x: 任意输入值（str / int / float / None）。

    Returns:
        int | None: 转换后的整数；空值或异常返回 ``None``。
    """
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
    """聚合求和，``None`` 视为缺失值。

    Args:
        a: 第一个值（可为 ``None``）。
        b: 第二个值（可为 ``None``）。

    Returns:
        两个值之和；若两者均为 ``None`` 则返回 ``None``。
    """
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return a + b


def _agg_int_sum(a, b):
    """聚合求和并转为整数。

    先调用 :func:`_agg_sum` 求和，再将结果转为 ``int``。

    Args:
        a: 第一个值（可为 ``None``）。
        b: 第二个值（可为 ``None``）。

    Returns:
        int | None: 求和后的整数值；两者均 ``None`` 或转换失败返回 ``None``。
    """
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
    """将 ``YYYYMM`` 格式标准化为 ``YYYY-MM``。

    Args:
        x (str | None): 月份字符串，如 ``"202501"`` 或 ``"2025-01"``。

    Returns:
        str | None: 标准化后的 ``YYYY-MM`` 字符串；输入为 ``None`` 或异常返回 ``None``。
    """
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
    """将比率值格式化为百分比字符串。

    若值在 ``[-1, 1]`` 范围内视为小数比例，自动乘以 100。

    Args:
        v: 比率值（float / str / None）。

    Returns:
        str: 格式化后的百分比字符串，如 ``"23.45%"``；空值返回 ``""``。
    """
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
    """根据月度指标判定 Excel 单元格颜色。

    判定规则（均要求毛利润 < 0）：
    - 退货率 > 15% 且 广告费率 > 10% → 红色 ``FFFF0000``
    - 退货率 > 15% 且 广告费率 ≤ 10% → 绿色 ``FF00AA00``
    - 退货率 ≤ 15% 且 广告费率 > 10% → 黄色 ``FFFFFF00``
    - 其余 → 无颜色（``None``）

    Args:
        month_vals (dict): 月度指标字典，需包含 ``gross_profit``、
            ``refund_amount_rate``、``spend_rate`` 键。

    Returns:
        str | None: ARGB 颜色字符串（如 ``"FFFF0000"``）；不匹配规则返回 ``None``。
    """
    try:
        gp = month_vals.get('gross_profit')
        refund = month_vals.get('refund_amount_rate')
        ad_rate = month_vals.get('spend_rate')

        def _norm_pct(v):
            """将百分比值标准化为 0-100 范围。

            若值在 ``[-1, 1]`` 内视为小数比例，乘以 100。
            """
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
    """根据查询参数构建 SHA256 缓存键。

    将所有影响导出结果的参数序列化为 JSON 并取 SHA256，确保相同查询参数命中同一缓存。

    Args:
        owner_q (str): 负责人筛选条件。
        time_range (str): 时间范围。
        stores (list): 店铺 ID 列表。
        months (list): 月份列表。
        batch_size (int): 批量大小。

    Returns:
        str | None: ``monthly_loss_xlsx_`` 前缀的 SHA256 缓存键；异常返回 ``None``。
    """
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
    """检查请求是否要求强制刷新缓存。

    检查 ``payload`` 中 ``refresh``、``refresh_cache``、``force_refresh`` 三个键，
    任一为真值或 ``"true"`` / ``"1"`` 等字符串即返回 ``True``。

    Args:
        payload (dict): 请求体解析后的字典。

    Returns:
        bool: 是否要求强制刷新。
    """
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
    """尝试从缓存获取已生成的 xlsx 文件响应。

    支持三种缓存存储格式：内存 bytes、磁盘路径、原始 bytes。

    Args:
        cache_key (str): 由 :func:`build_cache_key` 生成的缓存键。
        months (list[str]): 月份列表，用于生成文件名。

    Returns:
        FileResponse | None: 命中缓存则返回文件下载响应；未命中返回 ``None``。
    """
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
    """清除缓存键对应的内存缓存和磁盘临时文件。

    同时清理 Django cache 中的条目和 ``MEDIA_ROOT/export_cache/`` 目录下的
    对应 ``.xlsx`` 文件。

    Args:
        cache_key (str): 由 :func:`build_cache_key` 生成的缓存键。
    """
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
    """缓存 xlsx 二进制数据，内存缓存失败时回退到磁盘。

    优先尝试写入 Django cache（永不过期）；若 cache 后端拒绝大值，
    回退写入 ``MEDIA_ROOT/export_cache/{cache_key}.xlsx`` 并将路径存入 cache。

    Args:
        cache_key (str): 缓存键。
        data_bytes (bytes): xlsx 文件二进制内容。
        filename (str): 原始文件名。

    Returns:
        bool: 缓存成功返回 ``True``，完全失败返回 ``False``。
    """
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
    """将临时文件作为 HTTP 文件下载响应流式返回。

    响应发送后启动守护线程，延迟 ``delay`` 秒后删除临时文件。

    Args:
        tmp_name (str): 临时文件路径。
        filename (str): 下载文件名。
        delay (int): 文件清理延迟秒数，默认 30 秒。

    Returns:
        FileResponse | None: 文件下载响应；文件打开失败返回 ``None``。
    """
    try:
        from django.http import FileResponse
        f = open(tmp_name, 'rb')
        resp = FileResponse(f, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'

        def _cleanup_file(path_file, delay_sec=delay):
            """延迟删除临时文件。

            等待 ``delay_sec`` 秒后删除指定路径的文件，忽略所有异常。
            """
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

