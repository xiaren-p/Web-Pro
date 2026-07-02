"""操作日志统计查询选择器。

提供访问趋势 (7日 PV/UV/IP) 与访问统计 (今日/昨日/总量+增长率) 的只读聚合逻辑。
"""
import datetime

from django.db.models import Count
from django.db.models.functions import TruncDate

from apps.system.models import OperLog


def get_visit_trend() -> dict:
    """查询最近 7 天访问趋势，返回 ECharts 可直接消费的格式。

    Returns:
        dict: 含 dates / pvList / uvList / ipList 四个等长列表。
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
            ip_count=Count("ip", distinct=True),
        )
        .order_by("d")
    )

    date_list = [start_date + datetime.timedelta(days=i) for i in range(7)]
    m = {x["d"]: x for x in agg}

    return {
        "dates": [d.strftime("%Y-%m-%d") for d in date_list],
        "pvList": [m.get(d, {}).get("pv", 0) for d in date_list],
        "uvList": [m.get(d, {}).get("uv", 0) for d in date_list],
        "ipList": [m.get(d, {}).get("ip_count", 0) for d in date_list],
    }


def get_visit_stats() -> dict:
    """查询今日/昨日/总量访问统计及同比增长率。

    增长率已计算为百分比数值（后端定型），昨日为 0 时今日有值视为 100%。

    Returns:
        dict: 含 todayUvCount / totalUvCount / uvGrowthRate / todayPvCount / totalPvCount / pvGrowthRate。
    """
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    total_pv = OperLog.objects.count()
    total_uv = OperLog.objects.aggregate(c=Count("operator", distinct=True))["c"] or 0

    today_qs = OperLog.objects.filter(created_at__date=today)
    yesterday_qs = OperLog.objects.filter(created_at__date=yesterday)
    today_pv = today_qs.count()
    today_uv = today_qs.aggregate(c=Count("operator", distinct=True))["c"] or 0
    yesterday_pv = yesterday_qs.count()
    yesterday_uv = yesterday_qs.aggregate(c=Count("operator", distinct=True))["c"] or 0

    pv_growth = ((today_pv - yesterday_pv) / yesterday_pv * 100.0) if yesterday_pv else (100.0 if today_pv > 0 else 0.0)
    uv_growth = ((today_uv - yesterday_uv) / yesterday_uv * 100.0) if yesterday_uv else (100.0 if today_uv > 0 else 0.0)

    return {
        "todayUvCount": today_uv,
        "totalUvCount": total_uv,
        "uvGrowthRate": round(uv_growth, 2),
        "todayPvCount": today_pv,
        "totalPvCount": total_pv,
        "pvGrowthRate": round(pv_growth, 2),
    }
