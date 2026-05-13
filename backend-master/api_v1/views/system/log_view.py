"""操作/访问日志 ViewSet。

包含分页查询、最近 7 天访问趋势与今/昨日对比统计三个接口。
日期文本（如趋势图横坐标 ``YYYY-MM-DD``）已在后端定型，前端直接喂给 ECharts 即可。
"""
from __future__ import annotations

import datetime
import re
from typing import Any

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models import OperLog
from api_v1.permissions import MenuPermRequired
from api_v1.serializers import OperLogSerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok


def _parse_browser(ua: str) -> str:
    """从 UserAgent 字符串中解析浏览器名称与版本。

    顺序极其重要：Edge / Opera 的 UA 中均包含 Chrome 标记，必须优先匹配。
    """
    if not ua:
        return ""
    ua = str(ua)
    try:
        m = re.search(r"Edg/([\d\.]+)", ua)
        if m:
            return f"Edge {m.group(1)}"
        m = re.search(r"OPR/([\d\.]+)", ua)
        if m:
            return f"Opera {m.group(1)}"
        m = re.search(r"Chrome/([\d\.]+)", ua)
        if m and "Chromium" not in ua and "Edg/" not in ua:
            return f"Chrome {m.group(1)}"
        m = re.search(r"Firefox/([\d\.]+)", ua)
        if m:
            return f"Firefox {m.group(1)}"
        # Safari 版本号使用 Version/xx 而非 Safari/xx
        if "Safari/" in ua and "Chrome/" not in ua and "Chromium" not in ua:
            m = re.search(r"Version/([\d\.]+)", ua)
            if m:
                return f"Safari {m.group(1)}"
            return "Safari"
    except Exception:
        pass
    return ""


def _parse_os(ua: str) -> str:
    """从 UserAgent 字符串中解析操作系统名称与版本。"""
    if not ua:
        return ""
    ua = str(ua)
    try:
        m = re.search(r"Windows NT ([\d\.]+)", ua)
        if m:
            # 10.0 同时对应 Win10/Win11，进一步细分需更复杂的探测逻辑
            ver_map = {
                "10.0": "10/11", "6.3": "8.1", "6.2": "8",
                "6.1": "7", "6.0": "Vista", "5.1": "XP",
            }
            ver_raw = m.group(1)
            return f"Windows {ver_map.get(ver_raw, ver_raw)}"
        m = re.search(r"Android ([\d\.]+)", ua)
        if m:
            return f"Android {m.group(1)}"
        m = re.search(r"iPhone OS ([\d_]+)", ua)
        if m:
            return f'iOS {m.group(1).replace("_", ".")}'
        m = re.search(r"iPad; CPU OS ([\d_]+)", ua)
        if m:
            return f'iPadOS {m.group(1).replace("_", ".")}'
        m = re.search(r"Mac OS X ([\d_]+)", ua)
        if m:
            return f'macOS {m.group(1).replace("_", ".")}'
        if "Linux" in ua:
            return "Linux"
    except Exception:
        pass
    return ""


def _parse_region(ip: str) -> str:
    """根据 IP 段做轻量地区识别（避免引入第三方 GeoIP 依赖）。"""
    if not ip:
        return ""
    ip = str(ip)
    try:
        if ip.startswith("127.") or ip == "::1":
            return "本机"
        # 常见私有网段
        if ip.startswith("10.") or ip.startswith("192.168."):
            return "内网"
        if ip.startswith("172."):
            try:
                seg = int(ip.split(".")[1])
                if 16 <= seg <= 31:
                    return "内网"
            except Exception:
                pass
    except Exception:
        pass
    return "未知"


class LogViewSet(viewsets.ViewSet):
    """操作/访问日志接口。"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action_name = getattr(self, "action", None)
        method = (
            getattr(self.request, "method", "").upper()
            if hasattr(self, "request") else ""
        )
        required: list[str] | None = None
        if action_name == "page" and method == "GET":
            required = ["sys:log:view"]
        elif action_name == "visit_trend" and method == "GET":
            required = ["sys:log:trend"]
        elif action_name == "visit_stats" and method == "GET":
            required = ["sys:log:stats"]
        setattr(self, "required_perms", required)
        return super().get_permissions()

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request: Request) -> Any:
        """日志分页查询：支持关键字（module/action/operator/ip）与日期范围。

        UA / IP 全部在后端解析为可读字符串（浏览器、操作系统、地区），
        前端拿到后无需再做任何字段映射或换算。
        """
        qs = OperLog.objects.all().order_by("-id")

        keywords = request.query_params.get("keywords")
        if keywords:
            qs = qs.filter(
                Q(module__icontains=keywords)
                | Q(action__icontains=keywords)
                | Q(operator__icontains=keywords)
                | Q(ip__icontains=keywords)
            )

        date_range = (
            request.query_params.getlist("createTime[]")
            or request.query_params.getlist("createTime")
        )
        if date_range and len(date_range) >= 2 and date_range[0] and date_range[1]:
            try:
                start = datetime.datetime.strptime(date_range[0], "%Y-%m-%d")
                end = datetime.datetime.strptime(date_range[1], "%Y-%m-%d") + datetime.timedelta(days=1)
                qs = qs.filter(created_at__gte=start, created_at__lt=end)
            except Exception:
                pass

        total, items, _, _ = paginate_queryset(request, qs)
        raw = OperLogSerializer(items, many=True).data

        data = []
        for r in raw:
            ua = r.get("user_agent")
            ip = r.get("ip")
            data.append({
                "id": r.get("id"),
                "module": r.get("module"),
                "content": r.get("action") or "",
                "operator": r.get("operator"),
                "ip": ip,
                "region": _parse_region(ip),
                "browser": _parse_browser(ua),
                "os": _parse_os(ua),
                "createTime": r.get("created_at"),
                "executionTime": r.get("elapsed_ms"),
            })
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get"], url_path="visit-trend")
    def visit_trend(self, request: Request) -> Any:
        """最近 7 天访问趋势（PV / UV / IP）。

        日期已格式化为 ``YYYY-MM-DD`` 字符串，可直接喂给 ECharts xAxis。
        """
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=6)
        qs = OperLog.objects.filter(created_at__date__gte=start_date)
        agg = (
            qs.annotate(d=TruncDate("created_at"))
            .values("d")
            .annotate(
                pv=Count("id"),
                uv=Count("operator", distinct=True),
                ip=Count("ip", distinct=True),
            )
            .order_by("d")
        )
        # 构造完整 7 天序列，缺失日期补 0
        date_list = [start_date + datetime.timedelta(days=i) for i in range(7)]
        m = {x["d"]: x for x in agg}
        # 日期统一在后端格式化为前端可直接消费的字符串
        dates = [d.strftime("%Y-%m-%d") for d in date_list]
        pv_list = [m.get(d, {}).get("pv", 0) for d in date_list]
        uv_list = [m.get(d, {}).get("uv", 0) for d in date_list]
        ip_list = [m.get(d, {}).get("ip", 0) for d in date_list]
        return drf_ok({
            "dates": dates, "pvList": pv_list,
            "uvList": uv_list, "ipList": ip_list,
        })

    @action(detail=False, methods=["get"], url_path="visit-stats")
    def visit_stats(self, request: Request) -> Any:
        """今日 / 累计访问统计与同比增长率（已在后端定型为百分比数值）。"""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        total_pv = OperLog.objects.count()
        total_uv = OperLog.objects.aggregate(c=Count("operator", distinct=True))["c"] or 0

        qs_today = OperLog.objects.filter(created_at__date=today)
        qs_yest = OperLog.objects.filter(created_at__date=yesterday)
        today_pv = qs_today.count()
        today_uv = qs_today.aggregate(c=Count("operator", distinct=True))["c"] or 0
        y_pv = qs_yest.count()
        y_uv = qs_yest.aggregate(c=Count("operator", distinct=True))["c"] or 0

        # 增长率：昨日为 0 时今日有值视为 100%，均为 0 视为 0%
        pv_growth = ((today_pv - y_pv) / y_pv * 100.0) if y_pv else (100.0 if today_pv > 0 else 0.0)
        uv_growth = ((today_uv - y_uv) / y_uv * 100.0) if y_uv else (100.0 if today_uv > 0 else 0.0)

        return drf_ok({
            "todayUvCount": today_uv,
            "totalUvCount": total_uv,
            "uvGrowthRate": round(uv_growth, 2),
            "todayPvCount": today_pv,
            "totalPvCount": total_pv,
            "pvGrowthRate": round(pv_growth, 2),
        })
