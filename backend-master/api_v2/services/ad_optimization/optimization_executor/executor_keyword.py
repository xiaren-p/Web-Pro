"""SP 广告优化策略——关键词维度执行器。

对 auto_rules 中 comparison_target="keyword" 的规则执行，针对手动广告的关键词。

数据来源：LxSpKeyword（手动广告的关键词基础表）
报表来源：LxSpKeywordReport（关键词日报表）

执行链路（主入口 execute_keyword_rules）：
  1. 扫描 LxSpKeyword（状态=启用、竞价不为空）
  2. 前置快速跳过——逐条查上次竞价调整时间，周期未到则跳过
  3. 批量加载 sp_ad_optimization_strategy（投放类型=manual）+ LxSpCampaign（状态=开启）
  4. 提取 comparison_target="keyword" 的规则，按优先级升序执行，命中即停
  5. 竞价全局互斥——任一规则真正执行竞价，该关键词后续全部规则跳过

单条规则流程（_execute_single_rule）：
  a. 分时策略联动——linked_time_rules / linked_time_rules_exclude 判断
  b. 规则级条件组（组间 AND）——查关键词报表，所有组必须全通过
  c. 投放竞价操作——每条 targeting_bid_action 独立评估、独立执行
  d. 预算操作（占位）/ 其他操作（占位）
  e. 输出到本地 JSON 调试文件（临时）
"""
from __future__ import annotations

import json as _json
import logging
import os
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.db.models import Q, Sum

from api_v1.models.lingxing.ads.basic.lx_sp_ad_group import LxSpAdGroup
from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.basic.lx_sp_keyword import LxSpKeyword
from api_v1.models.lingxing.ads.report.lx_sp_keyword_report import LxSpKeywordReport
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

# 竞价最低保底值
MIN_BID_FLOOR = 0.02

# 条件组默认查询天数
DEFAULT_CONDITION_DAYS = 30

# 批量查询分片大小
BATCH_SIZE = 500

# 比对对象常量
COMPARISON_TARGET_KEYWORD = "keyword"


# ============================================================
# 通用工具
# ============================================================

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
    logger.info("[executor_keyword] 调试输出 %s", filepath)


# ============================================================
# 指标聚合与报表查询
# ============================================================

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
        包含基础指标与衍生指标的字典。
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


def _query_keyword_report(
    keyword_id: int,
    profile_id: int,
    days: int,
    today: date,
) -> dict[str, float] | None:
    """查询关键词近 N 天报表并聚合为指标字典。

    若三个核心指标（曝光、点击、花费）全为 0 则返回 None。

    Args:
        keyword_id: 关键词 ID
        profile_id: 店铺 ID
        days: 向前查询天数
        today: 基准日期

    Returns:
        指标字典或 None（无数据）。
    """
    date_start = today - timedelta(days=days)
    agg = (
        LxSpKeywordReport.objects
        .filter(
            keyword_id=keyword_id,
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


# ============================================================
# 分时策略联动
# ============================================================

def _check_time_pricing_link(rule: dict[str, Any], campaign_id: int, profile_id: int) -> bool:
    """分时策略联动检查。

    Args:
        rule: 规则 JSON
        campaign_id: 广告活动 ID
        profile_id: 店铺 ID

    Returns:
        True 表示通过。
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
            "[executor_keyword] 查分时记录失败 campaign=%d: %s",
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


# ============================================================
# 条件评估
# ============================================================

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
    logger.warning("[executor_keyword] 未知操作符 %s", operator)
    return False


def _evaluate_condition_set(condition_set: dict[str, Any], metrics: dict[str, float]) -> bool:
    """评估单个条件组（组内 AND），支持区间模式。

    Args:
        condition_set: 条件组 JSON
        metrics: 指标字典

    Returns:
        True 表示该组全部通过。
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
        metrics: 指标字典

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


# ============================================================
# 竞价计算
# ============================================================

def _calc_adjusted_bid(current_bid: float, bid_action: dict[str, Any]) -> float | None:
    """根据竞价操作类型计算调整后的竞价。

    支持四种操作：百分比降低/提高、固定值降低/提高。
    调整后竞价不低于 MIN_BID_FLOOR。

    Args:
        current_bid: 当前竞价
        bid_action: {"type", "value", "limit"}

    Returns:
        调整后竞价或 None（未知类型）。
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

    logger.warning("[executor_keyword] 未知竞价操作类型 %s", action_type)
    return None


# ============================================================
# 执行周期检查
# ============================================================

def _get_last_adjustment_time(
    keyword_id: int,
    campaign_id: int,
    profile_id: int,
) -> datetime | None:
    """查询关键词最近一次竞价调整成功记录的时间。

    Args:
        keyword_id: 关键词 ID
        campaign_id: 广告活动 ID
        profile_id: 店铺 ID

    Returns:
        adjustment_time 或 None。
    """
    last = (
        SpBidAdjustment.objects
        .filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
            keyword_id=keyword_id,
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
    """判断执行周期是否已满足。

    Args:
        last_time: 上次执行时间
        cycle_days: 执行周期天数

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
# 投放竞价操作
# ============================================================

def _execute_targeting_bid_actions(
    rule: dict[str, Any],
    keyword: dict,
    campaign: LxSpCampaign,
    today: date,
) -> tuple[list[dict[str, Any]], bool]:
    """对单个关键词执行竞价操作。维度级竞价使用规则级 bid_action。"""
    _ = campaign, today

    bid_action: dict[str, Any] = rule.get("bid_action") or {}
    bid_type = bid_action.get("type", "")
    if not bid_type or bid_type == "no_adjust":
        return [], False

    current_bid = float(keyword["bid"]) if keyword["bid"] else 0.0
    new_bid = _calc_adjusted_bid(current_bid, bid_action)
    if new_bid is None:
        return [{
            "状态": "跳过",
            "原因": f"不支持的竞价操作类型 {bid_type}",
            "关键词ID": keyword["keyword_id"],
        }], False

    if new_bid == current_bid:
        return [], False

    return [{
        "状态": "待执行",
        "关键词ID": keyword["keyword_id"], "关键词": keyword["keyword_text"],
        "调整前竞价": current_bid, "调整后竞价": round(new_bid, 4),
        "竞价操作类型": bid_type,
        "操作参数": {
            "type": bid_type,
            "value": bid_action.get("value"),
            "limit": bid_action.get("limit"),
        },
    }], True


# ============================================================
# 预算操作 / 其他操作（占位）
# ============================================================

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


# ============================================================
# 单条规则执行
# ============================================================

def _execute_single_rule(
    rule: dict[str, Any],
    keyword: dict,
    campaign: LxSpCampaign,
    today: date,
) -> tuple[dict[str, Any] | None, bool]:
    """对单个关键词执行单条规则。

    流程：分时联动 → 规则级条件组（组间 AND）→ 投放竞价 → 预算/其他（占位）。

    Args:
        rule: 规则 JSON
        keyword: LxSpKeyword 实例
        campaign: LxSpCampaign 实例
        today: 基准日期

    Returns:
        (结果字典或 None, 是否真正产生了竞价变动)。
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

    metrics = _query_keyword_report(keyword["keyword_id"], campaign.profile_id, max_days, today)
    passed, reason = _check_all_condition_sets(rule, metrics)
    if not passed:
        logger.info(
            "[executor_keyword] 规则「%s」(%s) kw=%d 条件组不通过: %s",
            rule_name, rule_id, keyword["keyword_id"], reason,
        )
        return None, False

    targeting_results, bid_executed = _execute_targeting_bid_actions(rule, keyword, campaign, today)
    budget_result = _execute_budget_action(rule)
    other_result = _execute_other_action(rule)

    result = {
        "规则ID": rule_id,
        "规则名称": rule_name,
        "优先级": rule.get("priority", 0),
        "广告活动ID": campaign.campaign_id,
        "店铺ID": campaign.profile_id,
        "关键词ID": keyword["keyword_id"],
        "关键词": keyword["keyword_text"],
        "当前竞价": float(keyword["bid"]) if keyword["bid"] else 0.0,
        "条件组结果": "通过",
        "报表数据": metrics,
        "预算操作": budget_result,
        "其他操作": other_result,
        "投放竞价操作": targeting_results,
    }
    _write_debug_file(f"kw_{keyword["keyword_id"]}_{rule_id}.json", result)
    return result, bid_executed


# ============================================================
# 规则提取
# ============================================================

def _extract_keyword_rules(auto_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 auto_rules 扁平结构中提取关键词维度规则，按优先级升序。

    Args:
        auto_rules: 扁平化匹配规则列表

    Returns:
        已排序的关键词维度规则列表。
    """
    rules: list[dict[str, Any]] = []
    for item in auto_rules:
        if isinstance(item, dict) and item.get("comparison_target") == COMPARISON_TARGET_KEYWORD:
            rules.extend(item.get("rules") or [])
    rules.sort(key=lambda r: r.get("priority", 0))
    return rules


# ============================================================
# 主入口
# ============================================================

def execute_keyword_rules() -> dict[str, Any]:
    """执行关键词维度的优化策略规则（主入口）。

    两步取巧：
      ① 前置周期跳过——扫描阶段逐条查上次竞价时间，周期未到跳过。
      ② 竞价全局互斥——任一规则真正执行竞价后，该关键词后续规则竞价跳过。

    Returns:
        {
            "扫描关键词数": int, "周期跳过数": int, "有策略匹配数": int,
            "执行规则数": int, "受影响关键词数": int,
            "结果详情": list[dict], "错误列表": list[str],
        }
    """
    today = date.today()
    _ensure_debug_dir()

    # ── 步骤 1：扫描所有可用的关键词（不限制个体竞价是否为空，后续用广告组竞价兜底）──
    keywords_raw = list(
        LxSpKeyword.objects
        .filter(state="enabled")
        .only("campaign_id", "profile_id", "keyword_id", "keyword_text", "bid", "ad_group_id")
    )
    if not keywords_raw:
        return {
            "扫描关键词数": 0, "周期跳过数": 0, "有策略匹配数": 0,
            "执行规则数": 0, "受影响关键词数": 0,
            "结果详情": [], "错误列表": [],
        }

    # ── 竞价继承：个体 bid → 广告组 default_bid；两者都为空则跳过 ──
    ad_group_ids = {k.ad_group_id for k in keywords_raw}
    ad_group_bid_map: dict[int, float] = {}
    if ad_group_ids:
        for ag in LxSpAdGroup.objects.filter(
            ad_group_id__in=list(ad_group_ids),
            default_bid__isnull=False,
        ).only("ad_group_id", "default_bid"):
            ad_group_bid_map[ag.ad_group_id] = float(ag.default_bid)

    keywords: list[dict] = []
    for k in keywords_raw:
        if k.bid is not None:
            bid = float(k.bid)
        else:
            bid = ad_group_bid_map.get(k.ad_group_id)
            if bid is None:
                continue
        keywords.append({
            "keyword_id": k.keyword_id,
            "campaign_id": k.campaign_id,
            "profile_id": k.profile_id,
            "keyword_text": k.keyword_text,
            "bid": bid,
            "ad_group_id": k.ad_group_id,
        })

    logger.info(
        "[executor_keyword] 扫描到 %d 个启用关键词",
        len(keywords),
    )

    # ── 步骤 2：前置周期跳过（仅针对竞价操作，不影响预算/其他操作）──
    cycle_skip_count = 0
    active_keywords: list[dict] = []
    for kw in keywords:
        last_time = _get_last_adjustment_time(
            kw["keyword_id"], kw["campaign_id"], kw["profile_id"],
        )
        ok, __ = _is_execution_cycle_ok(last_time, DEFAULT_CYCLE_DAYS)
        if not ok:
            cycle_skip_count += 1
            continue
        active_keywords.append(kw)

    logger.info(
        "[executor_keyword] 周期跳过 %d 个，进入执行 %d 个",
        cycle_skip_count, len(active_keywords),
    )
    if not active_keywords:
        return {
            "扫描关键词数": len(keywords),
            "周期跳过数": cycle_skip_count,
            "有策略匹配数": 0, "执行规则数": 0,
            "受影响关键词数": 0, "结果详情": [], "错误列表": [],
        }

    # ── 步骤 3：批量加载策略记录 + 广告活动 ──
    unique_pairs = list({(k["campaign_id"], k["profile_id"]) for k in active_keywords})
    strategy_map: dict[tuple[int, int, str], SpAdOptimizationStrategy] = {}
    campaign_map: dict[tuple[int, int], LxSpCampaign] = {}

    for i in range(0, len(unique_pairs), BATCH_SIZE):
        batch = unique_pairs[i:i + BATCH_SIZE]
        q = Q()
        for cid, pid in batch:
            q |= Q(campaign_id=cid, profile_id=pid)

        strategy_qs = SpAdOptimizationStrategy.objects.filter(
            q, rule_updated_today=True, targeting_type="manual",
        ).exclude(auto_rules=[])
        for s in strategy_qs:
            key = (s.campaign_id, s.profile_id, s.targeting_type)
            strategy_map[key] = s

        campaign_qs = LxSpCampaign.objects.filter(q, state="enabled")
        for c in campaign_qs:
            campaign_map[(c.campaign_id, c.profile_id)] = c

    logger.info("[executor_keyword] 策略记录匹配 %d 条", len(strategy_map))

    # ── 步骤 4：遍历执行（竞价全局互斥）──
    all_results: list[dict[str, Any]] = []
    errors: list[str] = []
    executed_rule_count = 0
    affected_keywords: set[int] = set()

    for kw in active_keywords:
        campaign = campaign_map.get((kw["campaign_id"], kw["profile_id"]))
        if campaign is None:
            continue

        strategy = strategy_map.get((kw["campaign_id"], kw["profile_id"], "manual"))
        if strategy is None:
            continue

        rules = _extract_keyword_rules(strategy.auto_rules)
        if not rules:
            continue

        bid_already_executed = False
        for rule in rules:
            if bid_already_executed:
                logger.info(
                    "[executor_keyword] kw=%d 已有规则执行竞价，跳过规则「%s」",
                    kw["keyword_id"], rule.get("rule_name", "?"),
                )
                continue

            try:
                result, bid_done = _execute_single_rule(rule, kw, campaign, today)
            except Exception as exc:
                error_msg = (
                    f"kw={kw["keyword_id"]} rule={rule.get('rule_id')} "
                    f"异常: {exc}"
                )
                logger.exception("[executor_keyword] %s", error_msg)
                errors.append(error_msg)
                continue

            if result is not None:
                all_results.append(result)
                executed_rule_count += 1
                affected_keywords.add(kw["keyword_id"])
                if bid_done:
                    bid_already_executed = True
                    break  # 竞价已执行，该关键词后续规则全部跳过
                # bid_done=False：条件通过但竞价无变化，继续尝试下一条规则

    logger.info(
        "[executor_keyword] 完成: active=%d, executed=%d, affected=%d, errors=%d",
        len(active_keywords), executed_rule_count,
        len(affected_keywords), len(errors),
    )

    return {
        "扫描关键词数": len(keywords),
        "周期跳过数": cycle_skip_count,
        "有策略匹配数": len(strategy_map),
        "执行规则数": executed_rule_count,
        "受影响关键词数": len(affected_keywords),
        "结果详情": all_results,
        "错误列表": errors,
    }
