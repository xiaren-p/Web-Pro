"""SP 广告优化策略执行器——公共工具模块。

提供 4 个维度执行器（campaign / targeting / keyword / product_targeting）共用的
指标构建、条件评估、竞价计算、分时联动、周期检查、预算/其他操作等无状态工具函数。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.db.models import Sum

from api_v1.models.lingxing.ads.report.lx_sp_target_report import LxSpTargetReport
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices,
    ExecutionTypeChoices,
    SpBidAdjustment,
)

logger = logging.getLogger(__name__)

# 竞价最低保底值
MIN_BID_FLOOR = 0.02

# 条件组默认查询天数
DEFAULT_CONDITION_DAYS = 30

# 默认执行周期（天）
DEFAULT_CYCLE_DAYS = 1

# 批量查询分片大小
BATCH_SIZE = 500

# 前端 targetGroup 值 → LxSpTarget.expression 中实际存储的 type 值
EXPR_TYPE_AUTO_MAP: dict[str, str] = {
    "close_match": "closeMatch",
    "loose_match": "looseMatch",
    "substitutes": "substitutes",
    "complements": "complements",
}


# ============================================================
# 指标聚合
# ============================================================

def build_metrics_dict(
    impressions: float,
    clicks: float,
    cost: float,
    orders: float,
    sales: float,
    units: float,
) -> dict[str, float]:
    """由聚合值构建标准化指标字典。

    Args:
        impressions: 曝光量汇总
        clicks: 点击量汇总
        cost: 花费汇总
        orders: 订单数汇总
        sales: 销售额汇总
        units: 销量汇总

    Returns:
        包含基础指标与衍生指标（CPA/ACoS/ROAS/CPC/CTR/CVR）的字典。
    """
    return {
        "impressions": impressions, "clicks": clicks,
        "cost": cost, "spend": cost,
        "orders": orders, "sales": sales,
        "adssales": sales, "units": units, "adsvolume": units,
        "cpa": cost / orders if orders > 0 else 0.0,
        "acos": (cost / sales * 100) if sales > 0 else 0.0,
        "roas": (sales / cost) if cost > 0 else 0.0,
        "cpc": cost / clicks if clicks > 0 else 0.0,
        "ctr": (clicks / impressions * 100) if impressions > 0 else 0.0,
        "cvr": (orders / clicks * 100) if clicks > 0 else 0.0,
        "spendspercent": 0.0, "adssalespercent": 0.0,
    }


def query_target_report(
    target_id: int,
    profile_id: int,
    days: int,
    today: date,
) -> dict[str, float] | None:
    """查询 LxSpTargetReport 近 N 天报表并聚合为指标字典。

    若三个核心指标（曝光、点击、花费）全为 0 则返回 None，
    表示无有效报表数据。

    Args:
        target_id: 定位组 / 商品投放 ID
        profile_id: 店铺 ID
        days: 向前查询天数
        today: 基准日期

    Returns:
        指标字典或 None（无数据）。
    """
    date_start = today - timedelta(days=days)
    agg = (
        LxSpTargetReport.objects
        .filter(
            target_id=target_id,
            profile_id=profile_id,
            report_date__gte=date_start,
            report_date__lte=today,
        )
        .aggregate(
            i=Sum("impressions"), c=Sum("clicks"), cost=Sum("cost"),
            o=Sum("orders"), s=Sum("sales"), u=Sum("units"),
        )
    )
    impressions_val = float(agg["i"] or 0)
    clicks_val = float(agg["c"] or 0)
    cost_val = float(agg["cost"] or 0)
    if impressions_val == 0 and clicks_val == 0 and cost_val == 0:
        return None
    return build_metrics_dict(
        impressions=impressions_val, clicks=clicks_val,
        cost=cost_val, orders=float(agg["o"] or 0),
        sales=float(agg["s"] or 0), units=float(agg["u"] or 0),
    )


# ============================================================
# 分时策略联动
# ============================================================

def check_time_pricing_link(
    rule: dict[str, Any],
    campaign_id: int,
    profile_id: int,
    logger_prefix: str = "",
) -> bool:
    """分时策略联动检查。

    逻辑：
      - linked_time_rules 与 linked_time_rules_exclude 均为空 → 不限，通过
      - 查 ad_time_pricing_hit 获取该广告活动的命中分时策略 ID
      - 如果命中 ID 在排除列表中 → 不通过
      - 如果设置了关联列表且命中 ID 不在其中 → 不通过

    Args:
        rule: 规则 JSON
        campaign_id: 广告活动 ID
        profile_id: 店铺 ID
        logger_prefix: 日志前缀（如 "[executor_keyword]"）

    Returns:
        True 表示分时联动条件通过。
    """
    linked_ids = rule.get("linked_time_rules") or []
    exclude_ids = rule.get("linked_time_rules_exclude") or []
    if not linked_ids and not exclude_ids:
        return True

    try:
        hit = AdTimePricingHit.objects.filter(
            campaign_id=campaign_id, profile_id=profile_id,
        ).first()
    except Exception as exc:
        logger.warning(
            "%s 查分时记录失败 campaign=%d: %s",
            logger_prefix, campaign_id, exc, exc_info=True,
        )
        return False

    hit_rule_ids: set[str] = set()
    if hit and hit.hit_time_pricing_rules:
        hit_rule_ids = set(str(hit.hit_time_pricing_rules).split(","))

    if exclude_ids:
        if hit_rule_ids & {str(x) for x in exclude_ids}:
            return False

    if linked_ids:
        if not (hit_rule_ids & {str(x) for x in linked_ids}):
            return False

    return True


# ============================================================
# 条件评估
# ============================================================

def evaluate_single_condition(actual: float, operator: str, target: float) -> bool:
    """评估单个条件（实际值 vs 阈值）。

    Args:
        actual: 实际指标值
        operator: 比较操作符（> < >= <= == !=）
        target: 阈值

    Returns:
        True 表示条件成立。
    """
    if operator == ">":
        return actual > target
    if operator == "<":
        return actual < target
    if operator == ">=":
        return actual >= target
    if operator == "<=":
        return actual <= target
    if operator == "==":
        return actual == target
    if operator == "!=":
        return actual != target
    logger.warning("未知操作符 %s", operator)
    return False


def evaluate_condition_set(
    condition_set: dict[str, Any],
    metrics: dict[str, float],
) -> bool:
    """评估单个条件组（组内 AND），支持区间模式。

    Args:
        condition_set: 条件组 JSON，含 conditions 列表和可选的 isRange 标记
        metrics: 指标字典

    Returns:
        True 表示该组所有条件均通过。
    """
    conditions = condition_set.get("conditions") or []
    if not conditions:
        return True

    for cond in conditions:
        metric_key = str(cond.get("metric", "")).lower()
        operator = str(cond.get("operator", ">"))
        value = float(cond.get("value", 0) or 0)

        actual = metrics.get(metric_key)
        if actual is None:
            actual = 0.0

        if not evaluate_single_condition(actual, operator, value):
            return False

        if bool(cond.get("isRange", False)):
            operator2 = str(cond.get("operator2", "<"))
            value2 = float(cond.get("value2", 0) or 0)
            if not evaluate_single_condition(actual, operator2, value2):
                return False

    return True


def check_all_condition_sets(
    rule: dict[str, Any],
    metrics: dict[str, float] | None,
) -> tuple[bool, str]:
    """检查规则的所有条件组是否全部通过（组间 AND）。

    Args:
        rule: 规则 JSON
        metrics: 指标字典（可为 None）

    Returns:
        (是否通过, 失败原因)。
    """
    condition_sets = rule.get("condition_sets") or []
    if not condition_sets:
        return True, ""

    if metrics is None:
        # 无报表数据视为全 0，继续评估条件
        metrics = {}

    for cs in condition_sets:
        if not evaluate_condition_set(cs, metrics):
            days = cs.get("days", "?")
            return False, f"条件组（近{days}天）未通过"

    return True, ""


# ============================================================
# 竞价计算
# ============================================================

def calc_adjusted_bid(current_bid: float, bid_action: dict[str, Any]) -> float | None:
    """根据竞价操作类型计算调整后的竞价。

    支持四种操作类型：
      - bid_percent_decrease：百分比降低，不低于 limit 和最低保底值
      - bid_percent_increase：百分比提高，不高于 limit
      - bid_fixed_decrease：固定值降低，不低于 limit 和最低保底值
      - bid_fixed_increase：固定值提高，不高于 limit

    Args:
        current_bid: 当前竞价
        bid_action: {"type", "value", "limit"}

    Returns:
        调整后竞价；未知操作类型返回 None。
    """
    action_type = bid_action.get("type", "")
    value = float(bid_action.get("value", 0) or 0)
    limit = bid_action.get("limit")
    limit_val = float(limit) if limit is not None else None

    if action_type == "bid_percent_decrease":
        new_bid = current_bid * (1 - value / 100)
        if limit_val is not None:
            new_bid = max(new_bid, limit_val)
        return max(new_bid, MIN_BID_FLOOR)

    if action_type == "bid_percent_increase":
        new_bid = current_bid * (1 + value / 100)
        if limit_val is not None:
            new_bid = min(new_bid, limit_val)
        return new_bid

    if action_type == "bid_fixed_decrease":
        new_bid = current_bid - value
        if limit_val is not None:
            new_bid = max(new_bid, limit_val)
        return max(new_bid, MIN_BID_FLOOR)

    if action_type == "bid_fixed_increase":
        new_bid = current_bid + value
        if limit_val is not None:
            new_bid = min(new_bid, limit_val)
        return new_bid

    logger.warning("未知竞价操作类型 %s", action_type)
    return None


# ============================================================
# 执行周期检查
# ============================================================

def get_last_adjustment_time(
    entity_type: str,
    entity_id: int,
    campaign_id: int,
    profile_id: int,
) -> datetime | None:
    """查询投放实体最近一次竞价调整成功记录的时间。

    Args:
        entity_type: 实体类型（"keyword" 或 "target"）
        entity_id: 实体 ID（关键词 ID 或定位组/商品投放 ID）
        campaign_id: 广告活动 ID
        profile_id: 店铺 ID

    Returns:
        adjustment_time 或 None（无历史记录）。
    """
    filter_kwargs: dict[str, Any] = {
        "campaign_id": campaign_id,
        "profile_id": profile_id,
        "execution_type": ExecutionTypeChoices.BID_ADJUSTMENT,
        "adjustment_status": AdjustmentStatusChoices.SUCCESS,
    }
    if entity_type == "keyword":
        filter_kwargs["keyword_id"] = entity_id
    else:
        filter_kwargs["target_id"] = entity_id

    last = (
        SpBidAdjustment.objects
        .filter(**filter_kwargs)
        .order_by("-adjustment_time")
        .first()
    )
    if last and last.adjustment_time:
        return last.adjustment_time
    return None


def is_execution_cycle_ok(
    last_time: datetime | None,
    cycle_days: int,
) -> tuple[bool, str]:
    """判断执行周期是否满足。

    Args:
        last_time: 上次执行时间（可为 None）
        cycle_days: 规则组配置的执行周期天数

    Returns:
        (是否满足, 原因说明)。
    """
    if last_time is None:
        return True, "首次调整，无历史记录"
    days_since = (datetime.now(dt_timezone.utc) - last_time).days
    if days_since < cycle_days:
        return False, f"执行周期未到（距上次 {days_since} 天，需 ≥ {cycle_days} 天）"
    return True, f"距上次 {days_since} 天，周期满足"


# ============================================================
# 预算操作 / 其他操作（占位）
# ============================================================

def execute_budget_action(rule: dict[str, Any]) -> dict[str, Any]:
    """规则级预算操作（占位）。

    Args:
        rule: 规则 JSON

    Returns:
        预算操作结果字典。
    """
    budget_action = rule.get("budget_action") or {}
    action_type = (budget_action or {}).get("type", "") if isinstance(budget_action, dict) else ""
    if not action_type or action_type == "no_adjust":
        return {"操作": "预算操作", "状态": "跳过", "原因": "无操作或不调整"}
    return {
        "操作": "预算操作", "状态": "占位",
        "类型": action_type,
        "值": budget_action.get("value"),
        "上限": budget_action.get("limit"),
    }


def execute_other_action(rule: dict[str, Any]) -> dict[str, Any]:
    """规则级其他操作——暂停/归档（占位）。

    Args:
        rule: 规则 JSON

    Returns:
        其他操作结果字典。
    """
    other_action = rule.get("other_action") or {}
    action_type = (other_action or {}).get("type", "") if isinstance(other_action, dict) else ""
    if not action_type or action_type == "no_other":
        return {"操作": "其他操作", "状态": "跳过", "原因": "无操作"}
    return {
        "操作": "其他操作", "状态": "占位",
        "类型": action_type,
        "通知": other_action.get("notify", False),
    }
