"""SP 广告优化策略——定位组维度执行器。

对 auto_rules 中 comparison_target="targeting" 的规则执行，针对自动广告的定位组。

数据来源：LxSpTarget（expression_type="auto"，定位组基础表）
报表来源：LxSpTargetReport（定位组日报表）

执行链路（主入口 execute_targeting_rules）：
  1. 扫描 LxSpTarget（表达式类型=自动、状态=启用、竞价不为空）
  2. 前置快速跳过——逐条查上次竞价调整时间，周期未到则跳过（省去所有报表查询）
  3. 批量加载 sp_ad_optimization_strategy（投放类型=自动）+ LxSpCampaign（状态=开启）
  4. 提取 comparison_target="targeting" 的规则，按优先级升序执行，命中即停
  5. 竞价全局互斥——任一规则真正执行竞价，该定位组后续全部规则跳过

单条规则流程（_execute_single_rule）：
  a. 分时策略联动——linked_time_rules / linked_time_rules_exclude 判断
  b. 规则级条件组（组间 AND）——查定位组报表，所有组必须全通过
  c. 投放竞价操作——每条 targeting_bid_action 独立评估、独立执行
  d. 预算操作（占位）/ 其他操作（占位）
  e. 输出到本地 JSON 调试文件（临时，后续改为写 SpBidAdjustment 表）
"""
from __future__ import annotations

import json as _json
import logging
import os
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.db.models import Q, Sum

from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.basic.lx_sp_target import LxSpTarget
from api_v1.models.lingxing.ads.report.lx_sp_target_report import LxSpTargetReport
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit
from api_v2.models.sp_ad_optimization_strategy import SpAdOptimizationStrategy
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices,
    ExecutionTypeChoices,
    SpBidAdjustment,
)

logger = logging.getLogger(__name__)

# 调试输出目录（临时，后续删除）
_DEBUG_DIR = os.path.join(os.path.dirname(__file__), "_debug_output")

# 默认执行周期（天），后续从 LxAdRuleGroup.execution_cycle 取
DEFAULT_CYCLE_DAYS = 1

# 竞价最低保底值（单位：货币）
MIN_BID_FLOOR = 0.02

# 条件组默认查询天数
DEFAULT_CONDITION_DAYS = 30

# 批量查询分片大小
BATCH_SIZE = 500

# 投放类型常量
EXPRESSION_TYPE_AUTO = "auto"

# 比对对象常量
COMPARISON_TARGET_TARGETING = "targeting"

# 前端定位组类型 → DB expression.type 映射
_TARGET_GROUP_TO_EXPR_TYPE: dict[str, str] = {
    "close_match": "closeMatch",
    "loose_match": "looseMatch",
    "substitutes": "substitutes",
    "complements": "complements",
}

# 定位组类型中文标签
_EXPR_TYPE_LABEL: dict[str, str] = {
    "closeMatch": "同类商品",
    "looseMatch": "紧密匹配",
    "substitutes": "关联商品",
    "complements": "宽泛匹配",
}


def _ensure_debug_dir() -> None:
    """确保调试输出目录存在。"""
    os.makedirs(_DEBUG_DIR, exist_ok=True)


def _write_debug_file(filename: str, data: Any) -> None:
    """将执行计划写入本地 JSON 调试文件（临时，后续删除）。

    Args:
        filename: 输出文件名
        data: 待序列化的执行计划数据
    """
    filepath = os.path.join(_DEBUG_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        _json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    logger.info("[executor_targeting] 调试输出 %s", filepath)


def _build_metrics_dict(
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


def _query_target_report(
    target_id: int,
    profile_id: int,
    days: int,
    today: date,
) -> dict[str, float] | None:
    """查询定位组近 N 天报表并聚合为指标字典。

    若三个核心指标（曝光、点击、花费）全为 0 则返回 None，
    表示无有效报表数据。

    Args:
        target_id: 定位组 ID
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
    return _build_metrics_dict(
        impressions=impressions_val, clicks=clicks_val,
        cost=cost_val, orders=float(agg["o"] or 0),
        sales=float(agg["s"] or 0), units=float(agg["u"] or 0),
    )


def _check_time_pricing_link(rule: dict[str, Any], campaign_id: int, profile_id: int) -> bool:
    """分时策略联动——规则中的关联分时/排除分时条件检查。

    逻辑：
      - linked_time_rules 与 linked_time_rules_exclude 均为空 → 不限，通过
      - 查 ad_time_pricing_hit 获取该广告活动的命中分时策略 ID
      - 如果命中 ID 在排除列表中 → 不通过
      - 如果设置了关联列表且命中 ID 不在其中 → 不通过

    Args:
        rule: 规则 JSON
        campaign_id: 广告活动 ID
        profile_id: 店铺 ID

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
            "[executor_targeting] 查分时记录失败 campaign=%d: %s",
            campaign_id, exc, exc_info=True,
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


def _evaluate_single_condition(actual: float, operator: str, target: float) -> bool:
    """评估单个条件（实际值 vs 阈值）。

    Args:
        actual: 实际指标值
        operator: 比较操作符
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
    logger.warning("[executor_targeting] 未知操作符 %s", operator)
    return False


def _evaluate_condition_set(condition_set: dict[str, Any], metrics: dict[str, float]) -> bool:
    """评估单个条件组（组内 AND）。

    支持区间模式（isRange + operator2 + value2）。

    Args:
        condition_set: 条件组 JSON
        metrics: 指标字典

    Returns:
        True 表示该组所有条件均通过（空条件组也视为通过）。
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
            return False

        if not _evaluate_single_condition(actual, operator, value):
            return False

        if bool(cond.get("isRange", False)):
            operator2 = str(cond.get("operator2", "<"))
            value2 = float(cond.get("value2", 0) or 0)
            if not _evaluate_single_condition(actual, operator2, value2):
                return False

    return True


def _check_all_condition_sets(rule: dict[str, Any], metrics: dict[str, float] | None) -> tuple[bool, str]:
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
        return False, "无报表数据"

    for cs in condition_sets:
        if not _evaluate_condition_set(cs, metrics):
            days = cs.get("days", "?")
            return False, f"条件组（近{days}天）未通过"

    return True, ""


def _calc_adjusted_bid(current_bid: float, bid_action: dict[str, Any]) -> float | None:
    """根据竞价操作计算调整后的竞价。

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

    logger.warning("[executor_targeting] 未知竞价操作类型 %s", action_type)
    return None


def _get_last_adjustment_time(
    target_id: int,
    campaign_id: int,
    profile_id: int,
) -> datetime | None:
    """查询定位组最近一次竞价调整成功记录的时间。

    Args:
        target_id: 定位组 ID
        campaign_id: 广告活动 ID
        profile_id: 店铺 ID

    Returns:
        adjustment_time 或 None（无历史记录）。
    """
    last = (
        SpBidAdjustment.objects
        .filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
            target_id=target_id,
            execution_type=ExecutionTypeChoices.BID_ADJUSTMENT,
            adjustment_status=AdjustmentStatusChoices.SUCCESS,
        )
        .order_by("-adjustment_time")
        .first()
    )
    if last and last.adjustment_time:
        return last.adjustment_time
    return None


def _is_execution_cycle_ok(last_time: datetime | None, cycle_days: int) -> tuple[bool, str]:
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


def _get_expression_type_label(expression: list | None) -> str:
    """从 LxSpTarget.expression JSON 中提取定位组类型中文名称。

    Args:
        expression: LxSpTarget.expression 字段值

    Returns:
        中文标签（如"同类商品"）。
    """
    if not expression or not isinstance(expression, list):
        return "未知"
    for item in expression:
        if isinstance(item, dict):
            raw_type = item.get("type", "")
            return _EXPR_TYPE_LABEL.get(raw_type, raw_type)
    return "未知"


def _is_target_group_match(target: LxSpTarget, target_groups: list[str]) -> bool:
    """判断定位组的 expression.type 是否在用户选择的定位组类型列表中。

    需做前端值 → DB 值映射（如 close_match → closeMatch）。

    Args:
        target: LxSpTarget 实例
        target_groups: 前端选择的定位组类型列表

    Returns:
        True 表示匹配。
    """
    for tg in target_groups:
        mapped = _TARGET_GROUP_TO_EXPR_TYPE.get(tg, tg)
        for item in (target.expression if isinstance(target.expression, list) else []):
            if isinstance(item, dict) and item.get("type", "") == mapped:
                return True
    return False


def _execute_targeting_bid_actions(
    rule: dict[str, Any],
    target: LxSpTarget,
    campaign: LxSpCampaign,
    today: date,
) -> tuple[list[dict[str, Any]], bool]:
    """对单个定位组执行投放竞价操作。

    每条 targeting_bid_action：
      - 匹配定位组类型，不匹配静默跳过
      - 竞价计算，新竞价 = 当前竞价时跳过
      - campaign / today 为签名保留
    """
    _ = campaign, today
    tba_list: list[dict[str, Any]] = rule.get("targeting_bid_actions") or []
    if not tba_list:
        return [], False

    bid_executed = False
    results: list[dict[str, Any]] = []

    for idx, tba in enumerate(tba_list):
        target_groups: list[str] = tba.get("targetingGroups") or []
        unlimited = bool(tba.get("unlimitedTargeting", False))
        bid_action: dict[str, Any] = tba.get("bidAction") or {}

        if not unlimited and not _is_target_group_match(target, target_groups):
            continue

        bid_type = bid_action.get("type", "")
        if not bid_type or bid_type == "no_adjust":
            results.append({"序号": idx, "状态": "跳过", "原因": "无竞价操作或操作类型为不调整"})
            continue

        current_bid = float(target.bid) if target.bid else 0.0
        new_bid = _calc_adjusted_bid(current_bid, bid_action)
        if new_bid is None:
            results.append({
                "序号": idx, "状态": "跳过",
                "原因": f"不支持的竞价操作类型 {bid_type}",
                "定位组ID": target.target_id,
            })
            continue

        if new_bid == current_bid:
            # 调整前后竞价相同，不写表
            continue

        bid_executed = True
        expr_label = _get_expression_type_label(target.expression)
        results.append({
            "序号": idx, "状态": "待执行",
            "定位组ID": target.target_id, "定位组类型": expr_label,
            "调整前竞价": current_bid, "调整后竞价": round(new_bid, 4),
            "竞价操作类型": bid_type,
            "操作参数": {
                "type": bid_type,
                "value": bid_action.get("value"),
                "limit": bid_action.get("limit"),
            },
        })

    return results, bid_executed


def _execute_budget_action(rule: dict[str, Any]) -> dict[str, Any]:
    """规则级预算操作（占位）。

    Args:
        rule: 规则 JSON

    Returns:
        预算操作结果。
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


def _execute_other_action(rule: dict[str, Any]) -> dict[str, Any]:
    """规则级其他操作——暂停/归档（占位）。

    Args:
        rule: 规则 JSON

    Returns:
        其他操作结果。
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


def _execute_single_rule(
    rule: dict[str, Any],
    target: LxSpTarget,
    campaign: LxSpCampaign,
    today: date,
) -> tuple[dict[str, Any] | None, bool]:
    """对单个定位组执行单条规则。

    流程：
      a. 分时策略联动检查
      b. 规则级条件组全通过
      c. 投放竞价操作
      d. 预算/其他操作（占位）
      e. 输出本地调试文件

    Args:
        rule: 规则 JSON
        target: LxSpTarget 实例
        campaign: LxSpCampaign 实例
        today: 基准日期

    Returns:
        (结果字典或 None, 是否真正产生了竞价变动)。
        竞价变动表示至少有一个投放竞价操作调整了竞价。
    """
    rule_id = rule.get("rule_id", "?")
    rule_name = rule.get("rule_name", "?")

    if not _check_time_pricing_link(rule, campaign.campaign_id, campaign.profile_id):
        return None, False

    max_days = DEFAULT_CONDITION_DAYS
    for cs in (rule.get("condition_sets") or []):
        days_val = int(cs.get("days", DEFAULT_CONDITION_DAYS) or DEFAULT_CONDITION_DAYS)
        if days_val > max_days:
            max_days = days_val

    metrics = _query_target_report(target.target_id, campaign.profile_id, max_days, today)
    passed, reason = _check_all_condition_sets(rule, metrics)
    if not passed:
        logger.info(
            "[executor_targeting] 规则「%s」(%s) tg=%d 条件组不通过: %s",
            rule_name, rule_id, target.target_id, reason,
        )
        return None, False

    targeting_results, bid_executed = _execute_targeting_bid_actions(rule, target, campaign, today)
    budget_result = _execute_budget_action(rule)
    other_result = _execute_other_action(rule)

    result = {
        "规则ID": rule_id,
        "规则名称": rule_name,
        "优先级": rule.get("priority", 0),
        "广告活动ID": campaign.campaign_id,
        "店铺ID": campaign.profile_id,
        "定位组ID": target.target_id,
        "定位组类型": _get_expression_type_label(target.expression),
        "当前竞价": float(target.bid) if target.bid else 0.0,
        "条件组结果": "通过",
        "报表数据": metrics,
        "预算操作": budget_result,
        "其他操作": other_result,
        "投放竞价操作": targeting_results,
    }
    _write_debug_file(f"tg_{target.target_id}_{rule_id}.json", result)
    return result, bid_executed


def _extract_targeting_rules(auto_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 auto_rules 扁平结构中提取比对对象为定位组的规则，按优先级升序。

    Args:
        auto_rules: 扁平化匹配规则列表

    Returns:
        已排序的定位组维度规则列表。
    """
    rules: list[dict[str, Any]] = []
    for item in auto_rules:
        if isinstance(item, dict) and item.get("comparison_target") == COMPARISON_TARGET_TARGETING:
            rules.extend(item.get("rules") or [])
    rules.sort(key=lambda r: r.get("priority", 0))
    return rules


def execute_targeting_rules() -> dict[str, Any]:
    """执行定位组维度的优化策略规则（主入口）。

    两步取巧：
      ① 前置周期跳过——扫描阶段逐条查上次竞价时间，周期未到直接跳过，
         省去报表查询，大幅减少无意义的 DB 开销。
      ② 竞价全局互斥——任一规则真正执行了竞价调整后，该定位组后续所有
         规则（含更低优先级的）的竞价操作全部跳过，避免重复调整。

    Returns:
        {
            "扫描定位组数": int,
            "周期跳过数": int,
            "有策略匹配数": int,
            "执行规则数": int,
            "受影响定位组数": int,
            "结果详情": list[dict],
            "错误列表": list[str],
        }
    """
    today = date.today()
    _ensure_debug_dir()

    # ── 步骤 1：扫描所有可用的定位组 ──
    targets = list(
        LxSpTarget.objects
        .filter(
            expression_type=EXPRESSION_TYPE_AUTO,
            state="enabled",
            bid__isnull=False,
        )
        .only("campaign_id", "profile_id", "target_id", "bid", "ad_group_id", "expression")
    )
    if not targets:
        return {
            "扫描定位组数": 0, "周期跳过数": 0, "有策略匹配数": 0,
            "执行规则数": 0, "受影响定位组数": 0,
            "结果详情": [], "错误列表": [],
        }
    logger.info(
        "[executor_targeting] 扫描到 %d 个启用定位组",
        len(targets),
    )

    # ── 步骤 2：前置周期跳过（逐条查上次竞价时间，仅影响竞价操作）──
    # 注意：周期检查只针对竞价调整操作，不影响预算操作和其他操作。
    #       即使周期未到、整条定位组跳过，后续如果有独立于竞价的全局操作也仍需评估。
    cycle_skip_count = 0
    active_targets: list[LxSpTarget] = []
    for target in targets:
        last_time = _get_last_adjustment_time(
            target.target_id, target.campaign_id, target.profile_id,
        )
        ok, __ = _is_execution_cycle_ok(last_time, DEFAULT_CYCLE_DAYS)
        if not ok:
            cycle_skip_count += 1
            continue
        active_targets.append(target)

    logger.info(
        "[executor_targeting] 周期跳过 %d 个，进入执行 %d 个",
        cycle_skip_count, len(active_targets),
    )

    if not active_targets:
        return {
            "扫描定位组数": len(targets),
            "周期跳过数": cycle_skip_count,
            "有策略匹配数": 0,
            "执行规则数": 0,
            "受影响定位组数": 0,
            "结果详情": [],
            "错误列表": [],
        }

    # ── 步骤 3：批量加载策略记录 + 广告活动 ──
    unique_pairs = list({(t.campaign_id, t.profile_id) for t in active_targets})
    strategy_map: dict[tuple[int, int, str], SpAdOptimizationStrategy] = {}
    campaign_map: dict[tuple[int, int], LxSpCampaign] = {}

    for i in range(0, len(unique_pairs), BATCH_SIZE):
        batch = unique_pairs[i:i + BATCH_SIZE]
        q = Q()
        for cid, pid in batch:
            q |= Q(campaign_id=cid, profile_id=pid)

        strategy_qs = SpAdOptimizationStrategy.objects.filter(
            q, rule_updated_today=True, targeting_type="auto",
        ).exclude(auto_rules=[])
        for s in strategy_qs:
            key = (s.campaign_id, s.profile_id, s.targeting_type)
            strategy_map[key] = s

        campaign_qs = LxSpCampaign.objects.filter(q, state="enabled")
        for c in campaign_qs:
            campaign_map[(c.campaign_id, c.profile_id)] = c

    logger.info(
        "[executor_targeting] 策略记录匹配 %d 条",
        len(strategy_map),
    )

    # ── 步骤 4：遍历执行（竞价全局互斥）──
    all_results: list[dict[str, Any]] = []
    errors: list[str] = []
    executed_rule_count = 0
    affected_targets: set[int] = set()

    for target in active_targets:
        campaign = campaign_map.get((target.campaign_id, target.profile_id))
        if campaign is None:
            continue

        strategy = strategy_map.get((target.campaign_id, target.profile_id, "auto"))
        if strategy is None:
            continue

        rules = _extract_targeting_rules(strategy.auto_rules)
        if not rules:
            continue

        # 竞价全局互斥标记
        bid_already_executed = False

        for rule in rules:
            if bid_already_executed:
                logger.info(
                    "[executor_targeting] tg=%d 已有规则执行竞价，跳过规则「%s」",
                    target.target_id, rule.get("rule_name", "?"),
                )
                continue

            try:
                result, bid_done = _execute_single_rule(rule, target, campaign, today)
            except Exception as exc:
                error_msg = (
                    f"tg={target.target_id} rule={rule.get('rule_id')} "
                    f"异常: {exc}"
                )
                logger.exception("[executor_targeting] %s", error_msg)
                errors.append(error_msg)
                continue

            if result is not None:
                all_results.append(result)
                executed_rule_count += 1
                affected_targets.add(target.target_id)
                if bid_done:
                    bid_already_executed = True
                break  # 命中即停

    logger.info(
        "[executor_targeting] 完成: active=%d, executed=%d, affected=%d, errors=%d",
        len(active_targets), executed_rule_count,
        len(affected_targets), len(errors),
    )

    return {
        "扫描定位组数": len(targets),
        "周期跳过数": cycle_skip_count,
        "有策略匹配数": len(strategy_map),
        "执行规则数": executed_rule_count,
        "受影响定位组数": len(affected_targets),
        "结果详情": all_results,
        "错误列表": errors,
    }
