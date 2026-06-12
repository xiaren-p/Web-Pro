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
  c. 竞价操作——检查条件组 → 调整竞价 → 写 SpBidAdjustment 表
  d. 预算操作（占位）/ 其他操作（占位）
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.db.models import Q, Sum

from api_v1.models.lingxing.ads.basic.lx_sp_ad_group import LxSpAdGroup
from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.basic.lx_sp_keyword import LxSpKeyword
from api_v1.models.lingxing.ads.report.lx_sp_keyword_report import LxSpKeywordReport
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
    apply_bid_update,
    build_metrics_dict,
    calc_adjusted_bid,
    check_all_condition_sets,
    check_time_pricing_link as _shared_check_time_pricing_link,
    execute_budget_action as _shared_execute_budget_action,
    execute_pause_archive_action,
    get_last_adjustment_time as _shared_get_last_adjustment_time,
    is_execution_cycle_ok as _shared_is_execution_cycle_ok,
    resolve_adjustment_status,
    resolve_rules,
)

logger = logging.getLogger(__name__)

COMPARISON_TARGET_KEYWORD = "keyword"


# ── 本地包装：适配旧调用方签名 ──
def _build_metrics_dict(*args: Any, **kwargs: Any) -> dict[str, float]:
    return build_metrics_dict(*args, **kwargs)


def _check_time_pricing_link(
    rule: dict[str, Any], campaign_id: int, profile_id: int,
) -> bool:
    return _shared_check_time_pricing_link(
        rule, campaign_id, profile_id, "[executor_keyword]",
    )


def _check_all_condition_sets(*args: Any, **kwargs: Any) -> tuple[bool, str]:
    return check_all_condition_sets(*args, **kwargs)


def _calc_adjusted_bid(*args: Any, **kwargs: Any) -> float | None:
    return calc_adjusted_bid(*args, **kwargs)


def _get_last_adjustment_time(
    keyword_id: int, campaign_id: int, profile_id: int,
) -> datetime | None:
    return _shared_get_last_adjustment_time(
        "keyword", keyword_id, campaign_id, profile_id,
    )


def _is_execution_cycle_ok(*args: Any, **kwargs: Any) -> tuple[bool, str]:
    return _shared_is_execution_cycle_ok(*args, **kwargs)


def _execute_budget_action(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _shared_execute_budget_action(*args, **kwargs)


def _execute_other_action(
    rule: dict[str, Any], keyword: dict, campaign: LxSpCampaign,
) -> dict[str, Any]:
    """规则级暂停/归档操作 —— 委托 _shared.execute_pause_archive_action。

    关键词维度：entity_type="keyword"，传入 keyword_id。
    """
    from api_v2.models.sp_ad_pause_archive import PauseArchiveEntityType

    return execute_pause_archive_action(
        rule,
        campaign_id=campaign.campaign_id,
        profile_id=campaign.profile_id,
        entity_type=PauseArchiveEntityType.KEYWORD,
        entity_id=keyword["keyword_id"],
    )


# ============================================================
# 报表查询（维度专属，不可抽离）
# ============================================================

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
# 投放竞价操作（维度专属）
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
    other_result = _execute_other_action(rule, keyword, campaign)

    # ── 写 SpBidAdjustment 表（仅竞价变动时写入）──
    if bid_executed:
        now = datetime.now(dt_timezone.utc)
        new_bid = None
        for tba_result in targeting_results:
            if isinstance(tba_result, dict) and tba_result.get("状态") == "待执行":
                new_bid = tba_result.get("调整后竞价")
                break
        bid_before = float(keyword["bid"]) if keyword["bid"] else 0.0
        adj_status, exec_status, msg = resolve_adjustment_status(
            campaign.campaign_id, campaign.profile_id,
            bid_before, float(new_bid) if new_bid else 0.0,
        )
        SpBidAdjustment.objects.create(
            keyword_id=keyword["keyword_id"],
            campaign_id=campaign.campaign_id,
            profile_id=campaign.profile_id,
            execution_type=ExecutionTypeChoices.BID_ADJUSTMENT,
            auto_rule_id=rule.get("rule_id"),
            bid_before=bid_before,
            bid_after=new_bid,
            adjustment_status=adj_status,
            execution_status=exec_status,
            msg=msg,
            adjustment_time=now,
        )
        # 同步更新实体表 bid
        if new_bid is not None:
            apply_bid_update("keyword", keyword["keyword_id"], float(new_bid))
        logger.info(
            "[executor_keyword] 写入 SpBidAdjustment kw=%d campaign=%d bid=%.4f→%.4f",
            keyword["keyword_id"], campaign.campaign_id,
            float(keyword["bid"]) if keyword["bid"] else 0.0, new_bid,
        )

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
        "竞价操作": targeting_results,
    }
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

    # ── 步骤 1.5：竞价继承 + 广告活动/广告组状态过滤 ──
    # 优先用关键词自身 bid，无 bid 则继承广告组 default_bid
    # 广告组 state != "enabled" 的关键词直接过滤（不可参与执行）
    ad_group_ids = {k.ad_group_id for k in keywords_raw}
    ad_group_map: dict[int, tuple[float | None, str]] = {}  # {ad_group_id: (default_bid, state)}
    if ad_group_ids:
        for ag in LxSpAdGroup.objects.filter(
            ad_group_id__in=list(ad_group_ids),
        ).only("ad_group_id", "default_bid", "state"):
            ad_group_map[ag.ad_group_id] = (
                float(ag.default_bid) if ag.default_bid is not None else None,
                ag.state or "",
            )

    ad_group_skip_count = 0
    keywords: list[dict] = []
    for k in keywords_raw:
        ag_info = ad_group_map.get(k.ad_group_id)
        ag_state = ag_info[1] if ag_info else ""
        ag_default_bid = ag_info[0] if ag_info else None

        # 广告组未启用 → 跳过
        if ag_state != "enabled":
            ad_group_skip_count += 1
            continue

        if k.bid is not None:
            bid = float(k.bid)
        else:
            if ag_default_bid is None:
                continue
            bid = ag_default_bid
        keywords.append({
            "keyword_id": k.keyword_id,
            "campaign_id": k.campaign_id,
            "profile_id": k.profile_id,
            "keyword_text": k.keyword_text,
            "bid": bid,
            "ad_group_id": k.ad_group_id,
        })

    logger.info(
        "[executor_keyword] 扫描到 %d 个启用关键词（广告组未启用跳过 %d 个）",
        len(keywords), ad_group_skip_count,
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
        ).exclude(auto_rules=[], manual_rules=[])
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

        rules = _extract_keyword_rules(resolve_rules(strategy))
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
