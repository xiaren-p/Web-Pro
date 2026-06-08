"""
广告指标聚合计算服务

将广告活动级 / 广告组级 / 投放级共用的聚合逻辑收拢于此，
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


def build_ad_metrics_map(
    ad_ids: list[str],
    campaign_id: str,
    profile_id: str,
    date_start: str | None,
    date_end: str | None,
    currency_icon: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    按 ad_id 聚合投放指标，使用"1 次 SQL + Python 两轮遍历"计算所有衍生指标及占比字段。

    为什么要接收 ad_ids 列表：
        lx_ad_metrics 表不含 ad_group_id 字段，只能通过上游（lx_ad_info）
        提前查出所属广告组的全量 ad_id 列表，再用 IN 子句过滤指标表。
        传入全量而非仅当前页，保证 % 类指标的分母覆盖完整范围。

    Args:
        ad_ids (list[str]): 当前广告组下的全量广告投放 ID 列表。
        campaign_id (str): 广告活动 ID，用于进一步隔离指标数据。
        profile_id (str): 店铺 Profile ID，防止跨店同 ad_id 碰撞。
        date_start (str | None): 起始日期，格式 YYYY-MM-DD；None 则不限制。
        date_end (str | None): 截止日期，格式 YYYY-MM-DD；None 则不限制。
        currency_icon (str): 货币符号，例如 "$"、"€"。

    Returns:
        tuple[dict[str, dict[str, Any]], dict[str, Any]]:
            - metrics_map: 以 ad_id（str）为键，各行指标字典为值的映射。
            - summary: 全量合计汇总行字典，供前端表格底部汇总行展示。
    """
    from api_v1.models.lingxing.ads.report.lx_sp_ad_report import LxSpAdReport

    if not ad_ids:
        return {}, _build_summary_row(0.0, 0.0, 0, 0, 0, 0.0, 0, 0, currency_icon)

    qs = LxSpAdReport.objects.filter(
        ad_id__in=ad_ids,
        campaign_id=campaign_id,
        profile_id=profile_id,
    )
    if date_start:
        qs = qs.filter(report_date__gte=date_start)
    if date_end:
        qs = qs.filter(report_date__lte=date_end)

    # 单次 GROUP BY 聚合，DB 端完成所有 SUM
    # 字段名映射：spends→cost, direct_sales→same_sales, direct_orders→same_orders, ad_units→units
    agg_rows = list(
        qs.values("ad_id").annotate(
            total_sales=Sum("sales"),
            total_same_sales=Sum("same_sales"),
            total_orders=Sum("orders"),
            total_same_orders=Sum("same_orders"),
            total_units=Sum("units"),
            total_cost=Sum("cost"),
            total_clicks=Sum("clicks"),
            total_impressions=Sum("impressions"),
        )
    )

    if not agg_rows:
        return {}, _build_summary_row(0.0, 0.0, 0, 0, 0, 0.0, 0, 0, currency_icon)

    # 第一轮遍历：累加全量合计，作为各 % 字段的分母基准
    tot_sales = tot_same_sales = tot_cost = 0.0
    tot_orders = tot_same_orders = tot_units = tot_clicks = tot_impressions = 0

    for row in agg_rows:
        tot_sales += float(row["total_sales"] or 0)
        tot_same_sales += float(row["total_same_sales"] or 0)
        tot_cost += float(row["total_cost"] or 0)
        tot_orders += int(row["total_orders"] or 0)
        tot_same_orders += int(row["total_same_orders"] or 0)
        tot_units += int(row["total_units"] or 0)
        tot_clicks += int(row["total_clicks"] or 0)
        tot_impressions += int(row["total_impressions"] or 0)

    # 第二轮遍历：基于合计计算每行衍生指标
    metrics_map: dict[str, dict[str, Any]] = {}
    for row in agg_rows:
        metrics_map[str(row["ad_id"])] = _compute_metrics_row(
            float(row["total_sales"] or 0),
            float(row["total_same_sales"] or 0),
            int(row["total_orders"] or 0),
            int(row["total_same_orders"] or 0),
            int(row["total_units"] or 0),
            float(row["total_cost"] or 0),
            int(row["total_clicks"] or 0),
            int(row["total_impressions"] or 0),
            currency_icon,
            tot_sales=tot_sales,
            tot_spends=tot_cost,
            tot_clicks=tot_clicks,
            tot_impressions=tot_impressions,
        )

    summary = _build_summary_row(
        tot_sales, tot_same_sales, tot_orders, tot_same_orders,
        tot_units, tot_cost, tot_clicks, tot_impressions,
        currency_icon,
    )
    return metrics_map, summary


# ────────────────────────────────────────────────────────────
#   自动投放定向条款指标（VARCHAR 字段，Python 侧聚合）
# ────────────────────────────────────────────────────────────

def _safe_float(val: Any) -> float:
    """
    将任意值安全转换为 float，失败或为空时返回 0.0。

    用于 lx_auto_targeting_metrics 表中所有 VARCHAR 指标字段的类型安全转换。

    Args:
        val (Any): 待转换值，通常为数据库 VARCHAR 原始字符串。

    Returns:
        float: 转换结果，失败则为 0.0。
    """
    try:
        return float(val) if val else 0.0
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val: Any) -> int:
    """
    将任意值安全转换为 int，失败或为空时返回 0。

    用于 lx_auto_targeting_metrics 表中所有 VARCHAR 整型指标字段的类型安全转换。

    Args:
        val (Any): 待转换值，通常为数据库 VARCHAR 原始字符串。

    Returns:
        int: 转换结果，失败则为 0。
    """
    try:
        return int(float(val)) if val else 0
    except (ValueError, TypeError):
        return 0


def empty_auto_targeting_metrics() -> dict[str, Any]:
    """
    返回自动投放定向条款指标字段的空默认值，供无指标数据的条款行填充占位。

    Returns:
        dict[str, Any]: 含所有指标字段（含 IS）的 "-" 占位字典。
    """
    base = empty_adgroup_metrics()
    base["is"] = "-"
    return base


def build_auto_targeting_metrics_map(
    target_ids: list[str],
    campaign_id: str,
    profile_id: str,
    date_start: str | None,
    date_end: str | None,
    currency_icon: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    按 target_id 聚合自动投放定向条款指标，返回 per-target 映射与汇总行。

    为什么用 Python 侧聚合而非 DB Sum()：
        lx_auto_targeting_metrics 表的所有指标字段均为 VARCHAR，
        Django ORM 的 Sum() 在 CharField 上不能做数值求和，
        因此在 Python 侧用 _safe_float / _safe_int 转换后逐行累加。
        逻辑等价于其他指标表的 GROUP BY + Sum()，只是数据类型处理层不同。

    IS（top_of_search_impression_share）字段取周期内有效值的均值，
    DB 存储为 0~1 小数，输出时乘以 100 转为百分比字符串。

    Args:
        target_ids (list[str]): 需要查询指标的 target_id 列表（来自 lx_auto_targeting_info）。
        campaign_id (str): 广告活动 ID，用于隔离指标数据。
        profile_id (str): 店铺 Profile ID，防止跨店同 target_id 碰撞。
        date_start (str | None): 起始日期 YYYY-MM-DD，None 则不限。
        date_end (str | None): 截止日期 YYYY-MM-DD，None 则不限。
        currency_icon (str): 货币符号，用于金额格式化。

    Returns:
        tuple[dict, dict]:
            - metrics_map: target_id → 完整指标展示字典（含 IS 字段）。
            - summary: 全量合计汇总行字典（IS 字段固定为 "-"）。
    """
    from api_v1.models.lingxing.ads.report.lx_sp_target_report import LxSpTargetReport

    if not target_ids:
        summary = _build_summary_row(0.0, 0.0, 0, 0, 0, 0.0, 0, 0, currency_icon)
        summary["is"] = "-"
        return {}, summary

    qs = LxSpTargetReport.objects.filter(
        target_id__in=target_ids,
        campaign_id=campaign_id,
        profile_id=profile_id,
    )
    if date_start:
        qs = qs.filter(report_date__gte=date_start)
    if date_end:
        qs = qs.filter(report_date__lte=date_end)

    rows = qs.values(
        "target_id",
        "sales",
        "same_sales",
        "orders",
        "same_orders",
        "units",
        "impressions",
        "clicks",
        "cost",
        "top_of_search_impression_share",
    )

    # 第一轮：按 target_id 累加原始 VARCHAR 值；IS 单独收集用于均值
    agg: dict[str, dict[str, Any]] = {}
    is_bucket: dict[str, list[float]] = {}

    for row in rows:
        tid = str(row["target_id"])

        if tid not in agg:
            agg[tid] = {
                "sales": 0.0,
                "same_sales": 0.0,
                "orders": 0,
                "same_orders": 0,
                "units": 0,
                "impressions": 0,
                "clicks": 0,
                "cost": 0.0,
            }
            is_bucket[tid] = []

        a = agg[tid]
        a["sales"] += _safe_float(row["sales"])
        a["same_sales"] += _safe_float(row["same_sales"])
        a["orders"] += _safe_int(row["orders"])
        a["same_orders"] += _safe_int(row["same_orders"])
        a["units"] += _safe_int(row["units"])
        a["impressions"] += _safe_int(row["impressions"])
        a["clicks"] += _safe_int(row["clicks"])
        a["cost"] += _safe_float(row["cost"])

        # 只收集格式合法的 IS 值，跳过空值与非数值字符串，避免拉低均值
        is_raw = row["top_of_search_impression_share"]
        if is_raw is not None and str(is_raw).strip() not in ("", "-", "N/A", "n/a"):
            try:
                is_bucket[tid].append(float(is_raw))
            except (ValueError, TypeError):
                pass

    # 全量合计（用于 % 分母，与 build_adgroup_metrics_map 第一轮逻辑一致）
    tot_sales = tot_same_sales = tot_cost = 0.0
    tot_orders = tot_same_orders = tot_units = tot_clicks = tot_impressions = 0

    for a in agg.values():
        tot_sales += a["sales"]
        tot_same_sales += a["same_sales"]
        tot_cost += a["cost"]
        tot_orders += a["orders"]
        tot_same_orders += a["same_orders"]
        tot_units += a["units"]
        tot_clicks += a["clicks"]
        tot_impressions += a["impressions"]

    # 第二轮：复用通用 _compute_metrics_row，追加 IS 字段
    metrics_map: dict[str, dict[str, Any]] = {}

    for tid, a in agg.items():
        is_list = is_bucket.get(tid, [])
        avg_is = sum(is_list) / len(is_list) if is_list else None
        is_str = f"{round(avg_is * 100, 2)}%" if avg_is is not None else "-"

        row_metrics = _compute_metrics_row(
            a["sales"],
            a["same_sales"],
            a["orders"],
            a["same_orders"],
            a["units"],
            a["cost"],
            a["clicks"],
            a["impressions"],
            currency_icon,
            tot_sales=tot_sales,
            tot_spends=tot_cost,
            tot_clicks=tot_clicks,
            tot_impressions=tot_impressions,
        )
        row_metrics["is"] = is_str
        metrics_map[tid] = row_metrics

    summary = _build_summary_row(
        tot_sales, tot_same_sales, tot_orders, tot_same_orders,
        tot_units, tot_cost, tot_clicks, tot_impressions,
        currency_icon,
    )
    summary["is"] = "-"
    return metrics_map, summary


# ────────────────────────────────────────────────────────────
#   否定投放公共指标计算（否定商品 + 否定关键词共用）
#   指标仅含 sales / orders / spends，无 clicks / impressions
# ────────────────────────────────────────────────────────────

def _compute_negative_row(
    r_sales: float,
    r_orders: int,
    r_spends: float,
    icon: str,
) -> dict[str, Any]:
    """
    根据单行聚合值计算否定投放指标字典。

    否定定向行无点击 / 曝光数据，只输出花费、销售额、订单数、ACoS 四项。

    Args:
        r_sales (float): 广告销售额。
        r_orders (int): 广告订单数。
        r_spends (float): 花费。
        icon (str): 货币符号。

    Returns:
        dict[str, Any]: 含 spends / adsSales / adsOrders / acos 的指标字典。
    """
    acos = f"{round(r_spends / r_sales * 100, 2)}%" if r_sales > 0 else "-"
    return {
        "spends": _fmt_money(r_spends, icon),
        "adsSales": _fmt_money(r_sales, icon),
        "adsOrders": r_orders,
        "acos": acos,
    }


def _build_negative_summary_row(
    tot_sales: float,
    tot_orders: int,
    tot_spends: float,
    icon: str,
) -> dict[str, Any]:
    """
    根据全量合计值构建否定投放汇总行。

    Args:
        tot_sales (float): 广告销售额合计。
        tot_orders (int): 广告订单合计。
        tot_spends (float): 花费合计。
        icon (str): 货币符号。

    Returns:
        dict[str, Any]: 汇总行展示字典。
    """
    acos = f"{round(tot_spends / tot_sales * 100, 2)}%" if tot_sales > 0 else "-"
    return {
        "spends": _fmt_money(tot_spends, icon),
        "adsSales": _fmt_money(tot_sales, icon),
        "adsOrders": tot_orders,
        "acos": acos,
    }


def empty_negative_metrics() -> dict[str, Any]:
    """
    返回否定投放指标字段的空默认值，供无指标数据的行填充占位。

    Returns:
        dict[str, Any]: 含 spends / adsSales / adsOrders / acos 的 "-" 占位字典。
    """
    return {
        "spends": "-",
        "adsSales": "-",
        "adsOrders": "-",
        "acos": "-",
    }


def build_auto_negative_targeting_metrics_map(
    target_ids: list[str],
    campaign_id: str,
    profile_id: str,
    date_start: str | None,
    date_end: str | None,
    currency_icon: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    按 target_id 聚合自动广告否定定向指标，返回 per-target 映射与汇总行。

    为什么用 Python 侧聚合而非 DB Sum()：
        lx_auto_negative_targeting_metrics 表的指标字段均为 VARCHAR，
        Django ORM Sum() 在 CharField 上不能做数值求和，
        与 build_auto_targeting_metrics_map 处理方式一致。

    Args:
        target_ids (list[str]): 需要查询指标的 target_id 列表。
        campaign_id (str): 广告活动 ID，用于隔离指标数据。
        profile_id (str): 店铺 Profile ID，防止跨店碰撞。
        date_start (str | None): 起始日期 YYYY-MM-DD，None 则不限。
        date_end (str | None): 截止日期 YYYY-MM-DD，None 则不限。
        currency_icon (str): 货币符号，用于金额格式化。

    Returns:
        tuple[dict, dict]:
            - metrics_map: target_id → 指标展示字典。
            - summary: 全量合计汇总行字典。
    """
    from api_v1.models.lingxing.ads.report.lx_sp_keyword_report import LxSpKeywordReport

    if not target_ids:
        return {}, _build_negative_summary_row(0.0, 0, 0.0, currency_icon)

    qs = LxSpKeywordReport.objects.filter(
        keyword_id__in=target_ids,
        campaign_id=campaign_id,
        profile_id=profile_id,
    )
    if date_start:
        qs = qs.filter(report_date__gte=date_start)
    if date_end:
        qs = qs.filter(report_date__lte=date_end)

    rows = qs.values("keyword_id", "sales", "orders", "cost")

    # 按 target_id 在 Python 侧累加
    agg: dict[str, dict[str, Any]] = {}
    for row in rows:
        tid = str(row["keyword_id"])
        if tid not in agg:
            agg[tid] = {"sales": 0.0, "orders": 0, "cost": 0.0}
        agg[tid]["sales"] += _safe_float(row["sales"])
        agg[tid]["orders"] += _safe_int(row["orders"])
        agg[tid]["cost"] += _safe_float(row["cost"])

    # 全量合计
    tot_sales = tot_cost = 0.0
    tot_orders = 0
    for a in agg.values():
        tot_sales += a["sales"]
        tot_cost += a["cost"]
        tot_orders += a["orders"]

    metrics_map: dict[str, dict[str, Any]] = {
        tid: _compute_negative_row(a["sales"], a["orders"], a["cost"], currency_icon)
        for tid, a in agg.items()
    }
    summary = _build_negative_summary_row(tot_sales, tot_orders, tot_cost, currency_icon)
    return metrics_map, summary


def build_negative_keyword_metrics_map(
    keyword_ids: list[str],
    campaign_id: str,
    profile_id: str,
    date_start: str | None,
    date_end: str | None,
    currency_icon: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    按 keyword_id 聚合否定关键词指标，返回 per-keyword 映射与汇总行。

    lx_negative_keyword_metrics 的指标字段为原生数值类型（decimal / int），
    直接使用 DB 端 GROUP BY + Sum() 聚合，效率优于 Python 侧逐行遍历。

    Args:
        keyword_ids (list[str]): 需要查询指标的 keyword_id 列表。
        campaign_id (str): 广告活动 ID，用于隔离指标数据。
        profile_id (str): 店铺 Profile ID，防止跨店碰撞。
        date_start (str | None): 起始日期 YYYY-MM-DD，None 则不限。
        date_end (str | None): 截止日期 YYYY-MM-DD，None 则不限。
        currency_icon (str): 货币符号，用于金额格式化。

    Returns:
        tuple[dict, dict]:
            - metrics_map: keyword_id → 指标展示字典。
            - summary: 全量合计汇总行字典。
    """
    from api_v1.models.lingxing.ads.report.lx_sp_keyword_report import LxSpKeywordReport

    if not keyword_ids:
        return {}, _build_negative_summary_row(0.0, 0, 0.0, currency_icon)

    qs = LxSpKeywordReport.objects.filter(
        keyword_id__in=keyword_ids,
        campaign_id=campaign_id,
        profile_id=profile_id,
    )
    if date_start:
        qs = qs.filter(report_date__gte=date_start)
    if date_end:
        qs = qs.filter(report_date__lte=date_end)

    agg_rows = list(
        qs.values("keyword_id").annotate(
            total_sales=Sum("sales"),
            total_orders=Sum("orders"),
            total_cost=Sum("cost"),
        )
    )

    if not agg_rows:
        return {}, _build_negative_summary_row(0.0, 0, 0.0, currency_icon)

    tot_sales = tot_cost = 0.0
    tot_orders = 0
    for row in agg_rows:
        tot_sales += float(row["total_sales"] or 0)
        tot_cost += float(row["total_cost"] or 0)
        tot_orders += int(row["total_orders"] or 0)

    metrics_map: dict[str, dict[str, Any]] = {
        str(row["keyword_id"]): _compute_negative_row(
            float(row["total_sales"] or 0),
            int(row["total_orders"] or 0),
            float(row["total_cost"] or 0),
            currency_icon,
        )
        for row in agg_rows
    }
    summary = _build_negative_summary_row(tot_sales, tot_orders, tot_cost, currency_icon)
    return metrics_map, summary

