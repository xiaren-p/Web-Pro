"""
广告指标聚合计算服务

将广告活动级 / 广告组级共用的聚合逻辑收拢于此，
供各 ViewSet 复用，杜绝跨层重复计算代码。

设计原则：
  1. 纯业务计算，无 HTTP 依赖，便于独立测试。
  2. 所有函数无状态，通过参数注入依赖，无隐式全局状态。
  3. 广告组级别必然归属于单一 campaign_id + profile_id，
     即单一货币，无需汇率换算，走最简路径。
  4. "1 次 SQL + Python 两轮遍历" 策略：
       - 第一轮：累加得到全量合计（totals），用于百分比分母。
       - 第二轮：基于合计逐行计算衍生指标。
     零额外 DB 查询，所有 % 字段在同一个服务调用内完成。
"""

from __future__ import annotations

from typing import Any

from django.db.models import Sum


# ────────────────────────────────────────────────────────────
#   私有辅助函数
# ────────────────────────────────────────────────────────────

def _fmt_money(value: float | int, icon: str) -> str:
    """
    将数值格式化为带货币符号的字符串，保留两位小数。

    Args:
        value (float | int): 待格式化的金额数值。
        icon (str): 货币符号，例如 "$"、"€"、"£"。

    Returns:
        str: 格式化后的字符串，例如 "€123.45"。
    """
    return f"{icon}{round(float(value), 2)}"


def _compute_metrics_row(
    r_sales: float,
    r_direct_sales: float,
    r_orders: int,
    r_direct_orders: int,
    r_ad_units: int,
    r_spends: float,
    r_clicks: int,
    r_impressions: int,
    icon: str,
    *,
    tot_sales: float,
    tot_spends: float,
    tot_clicks: int,
    tot_impressions: int,
) -> dict[str, Any]:
    """
    根据单行聚合原始值计算全部衍生指标字典。

    广告活动级与广告组级的指标公式完全相同，
    此函数作为二者共用的核心计算核心。

    Args:
        r_sales (float): 当前行广告销售额。
        r_direct_sales (float): 当前行直接销售额。
        r_orders (int): 当前行广告订单数。
        r_direct_orders (int): 当前行直接订单数。
        r_ad_units (int): 当前行广告销量。
        r_spends (float): 当前行花费。
        r_clicks (int): 当前行点击次数。
        r_impressions (int): 当前行曝光量。
        icon (str): 货币符号。
        tot_sales (float): 全量广告销售额合计（用于 adsSalesPercent 分母）。
        tot_spends (float): 全量花费合计（用于 spendsPercent 分母）。
        tot_clicks (int): 全量点击合计（用于 clicksPercent 分母）。
        tot_impressions (int): 全量曝光合计（用于 impressionsPercent 分母）。

    Returns:
        dict[str, Any]: 含所有展示字段的指标字典。
    """
    # ACoS = 花费 / 广告销售额 × 100%
    acos = f"{round(r_spends / r_sales * 100, 2)}%" if r_sales > 0 else "-"
    # ROAS = 广告销售额 / 花费（无量纲）
    roas = round(r_sales / r_spends, 2) if r_spends > 0 else "-"
    # CVR = 广告订单 / 点击 × 100%
    cvr = f"{round(r_orders / r_clicks * 100, 2)}%" if r_clicks > 0 else "-"
    # CTR = 点击 / 曝光 × 100%
    ctr = f"{round(r_clicks / r_impressions * 100, 2)}%" if r_impressions > 0 else "-"
    # CPC = 花费 / 点击（带货币符号）
    cpc_raw = round(r_spends / r_clicks, 2) if r_clicks > 0 else None
    # CPA = 花费 / 广告订单（带货币符号）
    cpa_raw = round(r_spends / r_orders, 2) if r_orders > 0 else None
    # 广告笔单价 = 广告销售额 / 广告订单
    order_price = _fmt_money(round(r_sales / r_orders, 2), icon) if r_orders > 0 else "-"

    return {
        "adsSales": _fmt_money(r_sales, icon),
        "adsSalesPercent": (
            f"{round(r_sales / tot_sales * 100, 2)}%"
            if tot_sales > 0 else "-"
        ),
        "directSales": _fmt_money(r_direct_sales, icon),
        "adsOrders": r_orders,
        "directOrders": r_direct_orders,
        "adsVolume": r_ad_units,
        "adsOrderPrice": order_price,
        "acos": acos,
        "roas": roas,
        "cvr": cvr,
        "impressions": r_impressions,
        "impressionsPercent": (
            f"{round(r_impressions / tot_impressions * 100, 2)}%"
            if tot_impressions > 0 else "-"
        ),
        "clicks": r_clicks,
        "clicksPercent": (
            f"{round(r_clicks / tot_clicks * 100, 2)}%"
            if tot_clicks > 0 else "-"
        ),
        "ctr": ctr,
        "cpc": _fmt_money(cpc_raw, icon) if cpc_raw is not None else "-",
        "spends": _fmt_money(r_spends, icon),
        "spendsPercent": (
            f"{round(r_spends / tot_spends * 100, 2)}%"
            if tot_spends > 0 else "-"
        ),
        "cpa": _fmt_money(cpa_raw, icon) if cpa_raw is not None else "-",
    }


def _build_summary_row(
    tot_sales: float,
    tot_direct_sales: float,
    tot_orders: int,
    tot_direct_orders: int,
    tot_ad_units: int,
    tot_spends: float,
    tot_clicks: int,
    tot_impressions: int,
    icon: str,
) -> dict[str, Any]:
    """
    根据全量合计值构建表格汇总行（summary），各 % 字段在汇总行中均为 "-"。

    Args:
        tot_sales (float): 广告销售额合计。
        tot_direct_sales (float): 直接销售额合计。
        tot_orders (int): 广告订单合计。
        tot_direct_orders (int): 直接订单合计。
        tot_ad_units (int): 广告销量合计。
        tot_spends (float): 花费合计。
        tot_clicks (int): 点击合计。
        tot_impressions (int): 曝光合计。
        icon (str): 货币符号。

    Returns:
        dict[str, Any]: 汇总行展示字典，占比类字段固定为 "-"。
    """
    acos = f"{round(tot_spends / tot_sales * 100, 2)}%" if tot_sales > 0 else "-"
    roas = round(tot_sales / tot_spends, 2) if tot_spends > 0 else "-"
    cvr = f"{round(tot_orders / tot_clicks * 100, 2)}%" if tot_clicks > 0 else "-"
    ctr = f"{round(tot_clicks / tot_impressions * 100, 2)}%" if tot_impressions > 0 else "-"
    cpc_raw = round(tot_spends / tot_clicks, 2) if tot_clicks > 0 else None
    cpa_raw = round(tot_spends / tot_orders, 2) if tot_orders > 0 else None
    order_price = (
        _fmt_money(round(tot_sales / tot_orders, 2), icon) if tot_orders > 0 else "-"
    )

    return {
        "adsSales": _fmt_money(tot_sales, icon),
        "adsSalesPercent": "-",
        "directSales": _fmt_money(tot_direct_sales, icon),
        "adsOrders": tot_orders,
        "directOrders": tot_direct_orders,
        "adsVolume": tot_ad_units,
        "adsOrderPrice": order_price,
        "acos": acos,
        "roas": roas,
        "cvr": cvr,
        "impressions": tot_impressions,
        "impressionsPercent": "-",
        "clicks": tot_clicks,
        "clicksPercent": "-",
        "ctr": ctr,
        "cpc": _fmt_money(cpc_raw, icon) if cpc_raw is not None else "-",
        "spends": _fmt_money(tot_spends, icon),
        "spendsPercent": "-",
        "cpa": _fmt_money(cpa_raw, icon) if cpa_raw is not None else "-",
    }


# ────────────────────────────────────────────────────────────
#   对外公开函数
# ────────────────────────────────────────────────────────────

def empty_adgroup_metrics() -> dict[str, Any]:
    """
    返回广告组指标字段的空默认值，供无指标数据的广告组填充占位。

    Returns:
        dict[str, Any]: 含所有指标字段的 "-" 占位字典。
    """
    return {
        "adsSales": "-",
        "adsSalesPercent": "-",
        "directSales": "-",
        "adsOrders": "-",
        "directOrders": "-",
        "adsVolume": "-",
        "adsOrderPrice": "-",
        "acos": "-",
        "roas": "-",
        "cvr": "-",
        "impressions": "-",
        "impressionsPercent": "-",
        "clicks": "-",
        "clicksPercent": "-",
        "ctr": "-",
        "cpc": "-",
        "spends": "-",
        "spendsPercent": "-",
        "cpa": "-",
    }


def build_adgroup_metrics_map(
    metrics_model: Any,
    campaign_id: str,
    profile_id: str,
    date_start: str | None,
    date_end: str | None,
    currency_icon: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    按 ad_group_id 聚合指标，使用"1 次 SQL + Python 两轮遍历"计算所有衍生指标及占比字段。

    为什么只需单一货币路径：
        广告组列表始终归属于同一个 campaign_id + profile_id，
        即同一店铺 → 同一国家 → 同一货币，不存在多货币换算需求。

    性能优化点：
        - 通过 GROUP BY ad_group_id 的单次 DB 聚合获取所有行数据。
        - 合计（totals）由同一批聚合行的 Python 累加推导，
          无需第二次 COUNT/SUM DB 查询。
        - 两轮遍历（第一轮求 totals，第二轮按比例计算 %）均在内存中完成，
          数据量（广告组数通常 < 500）远低于 I/O 瓶颈。

    Args:
        metrics_model (Any): LxAdGroupMetrics Django 模型类。
        campaign_id (str): 广告活动 ID，用于过滤指标表。
        profile_id (str): 店铺 Profile ID，防止跨店同 campaign_id 碰撞。
        date_start (str | None): 起始日期，格式 YYYY-MM-DD；None 则不限制。
        date_end (str | None): 截止日期，格式 YYYY-MM-DD；None 则不限制。
        currency_icon (str): 货币符号，例如 "$"、"€"。

    Returns:
        tuple[dict[str, dict[str, Any]], dict[str, Any]]:
            - metrics_map: 以 ad_group_id（str）为键，各行指标字典为值的映射。
            - summary: 全量合计汇总行字典，供前端表格底部汇总行展示。
    """
    qs = metrics_model.objects.filter(campaign_id=campaign_id, profile_id=profile_id)
    if date_start:
        qs = qs.filter(timestamp__gte=date_start)
    if date_end:
        qs = qs.filter(timestamp__lte=date_end)

    # 单次 GROUP BY 聚合，DB 端完成所有 SUM
    agg_rows = list(
        qs.values("ad_group_id").annotate(
            total_sales=Sum("sales"),
            total_direct_sales=Sum("direct_sales"),
            total_orders=Sum("orders"),
            total_direct_orders=Sum("direct_orders"),
            total_ad_units=Sum("ad_units"),
            total_spends=Sum("spends"),
            total_clicks=Sum("clicks"),
            total_impressions=Sum("impressions"),
        )
    )

    if not agg_rows:
        return {}, _build_summary_row(0.0, 0.0, 0, 0, 0, 0.0, 0, 0, currency_icon)

    # 第一轮遍历：累加全量合计，作为各 % 字段的分母基准
    tot_sales = tot_direct_sales = tot_spends = 0.0
    tot_orders = tot_direct_orders = tot_ad_units = tot_clicks = tot_impressions = 0

    for row in agg_rows:
        tot_sales += float(row["total_sales"] or 0)
        tot_direct_sales += float(row["total_direct_sales"] or 0)
        tot_spends += float(row["total_spends"] or 0)
        tot_orders += int(row["total_orders"] or 0)
        tot_direct_orders += int(row["total_direct_orders"] or 0)
        tot_ad_units += int(row["total_ad_units"] or 0)
        tot_clicks += int(row["total_clicks"] or 0)
        tot_impressions += int(row["total_impressions"] or 0)

    # 第二轮遍历：基于合计计算每行衍生指标
    metrics_map: dict[str, dict[str, Any]] = {}
    for row in agg_rows:
        metrics_map[str(row["ad_group_id"])] = _compute_metrics_row(
            float(row["total_sales"] or 0),
            float(row["total_direct_sales"] or 0),
            int(row["total_orders"] or 0),
            int(row["total_direct_orders"] or 0),
            int(row["total_ad_units"] or 0),
            float(row["total_spends"] or 0),
            int(row["total_clicks"] or 0),
            int(row["total_impressions"] or 0),
            currency_icon,
            tot_sales=tot_sales,
            tot_spends=tot_spends,
            tot_clicks=tot_clicks,
            tot_impressions=tot_impressions,
        )

    summary = _build_summary_row(
        tot_sales, tot_direct_sales, tot_orders, tot_direct_orders,
        tot_ad_units, tot_spends, tot_clicks, tot_impressions,
        currency_icon,
    )
    return metrics_map, summary
