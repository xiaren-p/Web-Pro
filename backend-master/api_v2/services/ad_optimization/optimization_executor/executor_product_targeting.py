"""SP 广告优化策略——商品投放维度执行器。

对 auto_rules 中 comparison_target="product_targeting" 的规则执行，针对手动广告的商品投放。

数据来源：LxSpTarget（expression_type="manual"）
报表来源：LxSpTargetReport（与定位组同一张表）

执行链路（主入口 execute_product_targeting_rules）：
  1. 扫描 LxSpTarget（表达式类型=手动、状态=启用、竞价不为空）
  2. 前置快速跳过——逐条查上次竞价调整时间，周期未到则跳过
  3. 批量加载 sp_ad_optimization_strategy（投放类型=manual）+ LxSpCampaign
  4. 提取 comparison_target="product_targeting" 的规则，按优先级升序执行
  5. 竞价全局互斥——任一规则真正执行竞价，该商品投放后续全部规则跳过

单条规则流程（_execute_single_rule）：
  a. 分时策略联动
  b. 规则级条件组（组间 AND）——查 LxSpTargetReport 报表
  c. 竞价操作——检查条件组 → 调整竞价 → 写 SpBidAdjustment 表
  d. 预算操作（占位）/ 其他操作（占位）
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone as dt_timezone
from typing import Any

from django.db.models import Q

from api_v1.models.lingxing.ads.basic.lx_sp_ad_group import LxSpAdGroup
from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.basic.lx_sp_target import LxSpTarget
from api_v2.models.sp_ad_optimization_strategy import SpAdOptimizationStrategy
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices,
    ExecutionTypeChoices,
    SpBidAdjustment,
)

from api_v2.services.ad_optimization.optimization_executor._shared import (
    BATCH_SIZE,
    DEFAULT_CONDITION_DAYS,
    DEFAULT_CYCLE_DAYS,
    calc_adjusted_bid,
    check_all_condition_sets,
    check_time_pricing_link as _shared_check_time_pricing_link,
    execute_budget_action as _shared_execute_budget_action,
    execute_other_action as _shared_execute_other_action,
    get_last_adjustment_time as _shared_get_last_adjustment_time,
    is_execution_cycle_ok as _shared_is_execution_cycle_ok,
    query_target_report,
)

logger = logging.getLogger(__name__)

COMPARISON_TARGET_PRODUCT_TARGETING = "product_targeting"
EXPRESSION_TYPE_MANUAL = "manual"


# ── 本地包装：适配旧调用方签名 ──
def _check_time_pricing_link(
    rule: dict[str, Any], campaign_id: int, profile_id: int,
) -> bool:
    return _shared_check_time_pricing_link(
        rule, campaign_id, profile_id, "[executor_product_targeting]",
    )


def _check_all_condition_sets(*args: Any, **kwargs: Any) -> tuple[bool, str]:
    return check_all_condition_sets(*args, **kwargs)


def _calc_adjusted_bid(*args: Any, **kwargs: Any) -> float | None:
    return calc_adjusted_bid(*args, **kwargs)


def _get_last_adjustment_time(
    target_id: int, campaign_id: int, profile_id: int,
) -> datetime | None:
    return _shared_get_last_adjustment_time(
        "target", target_id, campaign_id, profile_id,
    )


def _is_execution_cycle_ok(*args: Any, **kwargs: Any) -> tuple[bool, str]:
    return _shared_is_execution_cycle_ok(*args, **kwargs)


def _execute_budget_action(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _shared_execute_budget_action(*args, **kwargs)


def _execute_other_action(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _shared_execute_other_action(*args, **kwargs)


# ============================================================
# 报表查询（维度专属，不可抽离）
# ============================================================

def _query_target_report(
    target_id: int,
    profile_id: int,
    days: int,
    today: date,
) -> dict[str, float] | None:
    """查询商品投放近 N 天报表并聚合为指标字典（委托 _shared.query_target_report）。

    数据来源：LxSpTargetReport（expression_type=manual 的 target 共用此表）。

    Args:
        target_id: 商品投放 ID
        profile_id: 店铺 ID
        days: 向前查询天数
        today: 基准日期

    Returns:
        指标字典或 None（无有效数据）。
    """
    return query_target_report(target_id, profile_id, days, today)


# ============================================================
# 投放竞价操作（维度专属）
# ============================================================

def _execute_targeting_bid_actions(
    rule: dict[str, Any],
    product_target: dict,
    campaign: LxSpCampaign,
    today: date,
) -> tuple[list[dict[str, Any]], bool]:
    """对单个商品投放执行竞价操作。维度级竞价使用规则级 bid_action。"""
    _ = campaign, today

    bid_action: dict[str, Any] = rule.get("bid_action") or {}
    bid_type = bid_action.get("type", "")
    if not bid_type or bid_type == "no_adjust":
        return [], False

    current_bid = float(product_target["bid"]) if product_target["bid"] else 0.0
    new_bid = _calc_adjusted_bid(current_bid, bid_action)
    if new_bid is None:
        return [{
            "状态": "跳过",
            "原因": f"不支持的竞价操作类型 {bid_type}",
            "商品投放ID": product_target["target_id"],
        }], False

    if new_bid == current_bid:
        return [], False

    return [{
        "状态": "待执行",
        "商品投放ID": product_target["target_id"],
        "调整前竞价": current_bid, "调整后竞价": round(new_bid, 4),
        "竞价操作类型": bid_type,
        "操作参数": {
            "type": bid_type,
            "value": bid_action.get("value"),
            "limit": bid_action.get("limit"),
        },
    }], True


# ============================================================
# 单条规则执行
# ============================================================

def _execute_single_rule(
    rule: dict[str, Any],
    product_target: dict,
    campaign: LxSpCampaign,
    today: date,
) -> tuple[dict[str, Any] | None, bool]:
    """对单个商品投放执行单条规则。

    流程：分时联动 → 规则级条件组（组间 AND）→ 投放竞价 → 预算/其他（占位）。

    Args:
        rule: 规则 JSON
        product_target: LxSpTarget 实例
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

    metrics = _query_target_report(product_target["target_id"], campaign.profile_id, max_days, today)
    passed, reason = _check_all_condition_sets(rule, metrics)
    if not passed:
        logger.info(
            "[executor_product_targeting] 规则「%s」(%s) pt=%d 条件组不通过: %s",
            rule_name, rule_id, product_target["target_id"], reason,
        )
        return None, False

    targeting_results, bid_executed = _execute_targeting_bid_actions(rule, product_target, campaign, today)
    budget_result = _execute_budget_action(rule)
    other_result = _execute_other_action(rule)

    # ── 写 SpBidAdjustment 表（仅竞价变动时写入）──
    if bid_executed:
        now = datetime.now(dt_timezone.utc)
        new_bid = None
        for tba_result in targeting_results:
            if isinstance(tba_result, dict) and tba_result.get("状态") == "待执行":
                new_bid = tba_result.get("调整后竞价")
                break
        SpBidAdjustment.objects.create(
            target_id=product_target["target_id"],
            campaign_id=campaign.campaign_id,
            profile_id=campaign.profile_id,
            execution_type=ExecutionTypeChoices.BID_ADJUSTMENT,
            auto_rule_id=rule.get("rule_id"),
            bid_before=float(product_target["bid"]) if product_target["bid"] else 0.0,
            bid_after=new_bid,
            adjustment_status=AdjustmentStatusChoices.PENDING,
            adjustment_time=now,
        )
        logger.info(
            "[executor_product_targeting] 写入 SpBidAdjustment pt=%d campaign=%d bid=%.4f→%.4f",
            product_target["target_id"], campaign.campaign_id,
            float(product_target["bid"]) if product_target["bid"] else 0.0, new_bid,
        )

    result = {
        "规则ID": rule_id,
        "规则名称": rule_name,
        "优先级": rule.get("priority", 0),
        "广告活动ID": campaign.campaign_id,
        "店铺ID": campaign.profile_id,
        "商品投放ID": product_target["target_id"],
        "当前竞价": float(product_target["bid"]) if product_target["bid"] else 0.0,
        "条件组结果": "通过",
        "报表数据": metrics,
        "预算操作": budget_result,
        "其他操作": other_result,
        "竞价操作": targeting_results,
    }
    return result, bid_executed


# ============================================================
# 规则提取
# ============================================================

def _extract_product_targeting_rules(auto_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 auto_rules 扁平结构中提取商品投放维度规则，按优先级升序。

    Args:
        auto_rules: 扁平化匹配规则列表

    Returns:
        已排序的商品投放维度规则列表。
    """
    rules: list[dict[str, Any]] = []
    for item in auto_rules:
        if isinstance(item, dict) and item.get("comparison_target") == COMPARISON_TARGET_PRODUCT_TARGETING:
            rules.extend(item.get("rules") or [])
    rules.sort(key=lambda r: r.get("priority", 0))
    return rules


# ============================================================
# 主入口
# ============================================================

def execute_product_targeting_rules() -> dict[str, Any]:
    """执行商品投放维度的优化策略规则（主入口）。

    两步取巧：
      ① 前置周期跳过——扫描阶段逐条查上次竞价时间，周期未到跳过。
      ② 竞价全局互斥——任一规则真正执行竞价后，该商品投放后续规则竞价跳过。
    """
    today = date.today()

    # ── 步骤 1：扫描所有可用的商品投放（不限制个体竞价是否为空，后续用广告组竞价兜底）──
    product_targets_raw = list(
        LxSpTarget.objects
        .filter(
            expression_type=EXPRESSION_TYPE_MANUAL,
            state="enabled",
        )
        .only("campaign_id", "profile_id", "target_id", "bid", "ad_group_id", "expression")
    )
    if not product_targets_raw:
        return {
            "扫描商品投放数": 0, "周期跳过数": 0, "有策略匹配数": 0,
            "执行规则数": 0, "受影响商品投放数": 0,
            "结果详情": [], "错误列表": [],
        }

    # ── 竞价继承 + 广告活动/广告组状态过滤 ──
    # 优先用商品投放自身 bid，无 bid 则继承广告组 default_bid
    # 广告组 state != "enabled" 的商品投放直接过滤（不可参与执行）
    ad_group_ids = {t.ad_group_id for t in product_targets_raw}
    ad_group_map: dict[int, tuple[float | None, str]] = {}
    if ad_group_ids:
        for ag in LxSpAdGroup.objects.filter(
            ad_group_id__in=list(ad_group_ids),
        ).only("ad_group_id", "default_bid", "state"):
            ad_group_map[ag.ad_group_id] = (
                float(ag.default_bid) if ag.default_bid is not None else None,
                ag.state or "",
            )

    ad_group_skip_count = 0
    product_targets: list[dict] = []
    for t in product_targets_raw:
        ag_info = ad_group_map.get(t.ad_group_id)
        ag_state = ag_info[1] if ag_info else ""
        ag_default_bid = ag_info[0] if ag_info else None

        # 广告组未启用 → 跳过
        if ag_state != "enabled":
            ad_group_skip_count += 1
            continue

        if t.bid is not None:
            bid = float(t.bid)
        else:
            if ag_default_bid is None:
                continue
            bid = ag_default_bid
        product_targets.append({
            "target_id": t.target_id,
            "campaign_id": t.campaign_id,
            "profile_id": t.profile_id,
            "bid": bid,
            "ad_group_id": t.ad_group_id,
            "expression": t.expression,
        })

    logger.info(
        "[executor_product_targeting] 扫描到 %d 个启用商品投放（广告组未启用跳过 %d 个）",
        len(product_targets), ad_group_skip_count,
    )

    # ── 步骤 2：前置周期跳过（仅针对竞价操作，不影响预算/其他操作）──
    cycle_skip_count = 0
    active_product_targets: list[dict] = []
    for pt in product_targets:
        last_time = _get_last_adjustment_time(
            pt["target_id"], pt["campaign_id"], pt["profile_id"],
        )
        ok, __ = _is_execution_cycle_ok(last_time, DEFAULT_CYCLE_DAYS)
        if not ok:
            cycle_skip_count += 1
            continue
        active_product_targets.append(pt)

    logger.info(
        "[executor_product_targeting] 周期跳过 %d 个，进入执行 %d 个",
        cycle_skip_count, len(active_product_targets),
    )
    if not active_product_targets:
        return {
            "扫描商品投放数": len(product_targets),
            "周期跳过数": cycle_skip_count,
            "有策略匹配数": 0, "执行规则数": 0,
            "受影响商品投放数": 0, "结果详情": [], "错误列表": [],
        }

    # ── 步骤 3：批量加载策略记录 + 广告活动 ──
    unique_pairs = list({(t["campaign_id"], t["profile_id"]) for t in active_product_targets})
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

    logger.info("[executor_product_targeting] 策略记录匹配 %d 条", len(strategy_map))

    # ── 步骤 4：遍历执行（竞价全局互斥）──
    all_results: list[dict[str, Any]] = []
    errors: list[str] = []
    executed_rule_count = 0
    affected_product_targets: set[int] = set()

    for pt in active_product_targets:
        campaign = campaign_map.get((pt["campaign_id"], pt["profile_id"]))
        if campaign is None:
            continue

        strategy = strategy_map.get((pt["campaign_id"], pt["profile_id"], "manual"))
        if strategy is None:
            continue

        rules = _extract_product_targeting_rules(strategy.auto_rules)
        if not rules:
            continue

        bid_already_executed = False
        for rule in rules:
            if bid_already_executed:
                logger.info(
                    "[executor_product_targeting] pt=%d 已有规则执行竞价，跳过规则「%s」",
                    pt["target_id"], rule.get("rule_name", "?"),
                )
                continue

            try:
                result, bid_done = _execute_single_rule(rule, pt, campaign, today)
            except Exception as exc:
                error_msg = (
                    f"pt={pt["target_id"]} rule={rule.get('rule_id')} "
                    f"异常: {exc}"
                )
                logger.exception("[executor_product_targeting] %s", error_msg)
                errors.append(error_msg)
                continue

            if result is not None:
                all_results.append(result)
                executed_rule_count += 1
                affected_product_targets.add(pt["target_id"])
                if bid_done:
                    bid_already_executed = True
                    break  # 竞价已执行，该商品投放后续规则全部跳过
                # bid_done=False：条件通过但竞价无变化，继续尝试下一条规则

    logger.info(
        "[executor_product_targeting] 完成: active=%d, executed=%d, affected=%d, errors=%d",
        len(active_product_targets), executed_rule_count,
        len(affected_product_targets), len(errors),
    )

    return {
        "扫描商品投放数": len(product_targets),
        "周期跳过数": cycle_skip_count,
        "有策略匹配数": len(strategy_map),
        "执行规则数": executed_rule_count,
        "受影响商品投放数": len(affected_product_targets),
        "结果详情": all_results,
        "错误列表": errors,
    }
