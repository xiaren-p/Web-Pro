"""SP 广告优化策略——广告活动维度执行器（executor_campaign）。

对 auto_rules 中 comparison_target="campaign" 的规则执行。

执行链路（主入口 execute_campaign_rules）：
  1. 扫描 LxSpCampaign（状态为开启）
  2. 以 (广告活动ID, 店铺ID, 投放类型) 去 sp_ad_optimization_strategy 匹配
  3. 提取 campaign 维度的规则，按优先级升序执行，命中即停

单条规则的执行流程（_execute_campaign_rule）：
  a. 分时策略联动检查 —— 规则中设置了关联/排除分时策略时，需命中/未命中对应分时策略才继续
  b. 条件组评估 —— 组间 AND（所有条件组必须全部通过），组内 AND（组内条件必须全部满足）
      先检查广告活动创建天数是否 ≥ 条件组要求天数，不足则整条规则跳过；
      然后查询广告活动报表（近 N 天聚合），判断条件是否成立
  c. 条件全部通过后，执行三类操作（三者独立并行）：
     ┌─ 投放竞价操作（targeting_bid_actions）—— 完整实现
     │   ├─ 自动广告 → 定位组（LxSpTarget expression_type=auto）+ LxSpTargetReport
     │   └─ 手动广告 → 关键词（LxSpKeyword）+ LxSpKeywordReport
     │                  → 商品投放（LxSpTarget expression_type=manual）+ LxSpTargetReport
     │   每条 targeting_bid_action 之间互不影响；
     │   单条内部：筛选投放实体 → 逐实体查报表 → 条件组 AND 全通过 → 竞价调整
     ├─ 预算操作（budget_action）—— 占位
     └─ 其他操作（other_action）—— 占位（暂停/归档）
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.db.models import Q, Sum

from api_v1.models.lingxing.ads.basic.lx_sp_ad_group import LxSpAdGroup
from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.basic.lx_sp_keyword import LxSpKeyword
from api_v1.models.lingxing.ads.basic.lx_sp_target import LxSpTarget
from api_v1.models.lingxing.ads.report.lx_sp_campaign_report import LxSpCampaignReport
from api_v1.models.lingxing.ads.report.lx_sp_keyword_report import LxSpKeywordReport
from api_v1.models.lingxing.ads.report.lx_sp_target_report import LxSpTargetReport
from api_v2.models.sp_ad_optimization_strategy import SpAdOptimizationStrategy
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices,
    ExecutionTypeChoices,
    SpBidAdjustment,
)

from api_v2.services.ad_optimization.optimization_executor._shared import (
    EXPR_TYPE_AUTO_MAP,
    apply_bid_update,
    build_metrics_dict,
    calc_adjusted_bid,
    check_time_pricing_link as _shared_check_time_pricing_link,
    evaluate_condition_set,
    execute_budget_action as _shared_execute_budget_action,
    execute_pause_archive_action,
    resolve_adjustment_status,
    resolve_rules,
)

logger = logging.getLogger(__name__)

# ============================================================
# 常量
# ============================================================

COMPARISON_TARGET_CAMPAIGN = "campaign"


def _parse_creation_date(raw_val: Any) -> date | None:
    """将 campaign 的创建时间（毫秒时间戳）转为 date 对象。"""
    if raw_val is None:
        return None
    try:
        ts_ms = int(raw_val)
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=dt_timezone.utc).date()
    except (ValueError, OSError, TypeError):
        return None


def _build_metrics_dict(
    impressions: float,
    clicks: float,
    cost: float,
    orders: float,
    sales: float,
    units: float,
) -> dict[str, float]:
    """由聚合值构建标准化指标字典（委托 _shared.build_metrics_dict）。"""
    return build_metrics_dict(impressions, clicks, cost, orders, sales, units)


# ============================================================
# 步骤 a：分时策略联动检查
# ============================================================

def _check_time_pricing_link(
    rule: dict[str, Any],
    campaign_id: int,
    profile_id: int,
) -> bool:
    """检查规则中"关联分时策略 / 排除分时策略"是否满足（委托 _shared）。

    逻辑：
      - 规则中 linked_time_rules（关联分时）和 linked_time_rules_exclude（排除分时）
        都为空 → 跳过此步，不限制
      - 去 ad_time_pricing_hit 表查该广告活动的命中分时策略 ID
      - 如果设置了排除列表，且命中的分时 ID 在排除列表中 → 不通过
      - 如果设置了关联列表，且命中的分时 ID 不在关联列表中 → 不通过
    """
    return _shared_check_time_pricing_link(rule, campaign_id, profile_id, "[executor_campaign]")


# ============================================================
# 报表查询
# ============================================================

def _aggregate_campaign_report(
    campaign_id: int,
    profile_id: int,
    days: int,
    today: date,
) -> dict[str, float]:
    """查询广告活动近 N 天报表，聚合为指标字典。"""
    date_start = today - timedelta(days=days)
    agg = LxSpCampaignReport.objects.filter(
        campaign_id=campaign_id,
        profile_id=profile_id,
        report_date__gte=date_start,
        report_date__lte=today,
    ).aggregate(
        total_impressions=Sum("impressions"),
        total_clicks=Sum("clicks"),
        total_cost=Sum("cost"),
        total_orders=Sum("orders"),
        total_sales=Sum("sales"),
        total_units=Sum("units"),
    )
    return _build_metrics_dict(
        impressions=float(agg["total_impressions"] or 0),
        clicks=float(agg["total_clicks"] or 0),
        cost=float(agg["total_cost"] or 0),
        orders=float(agg["total_orders"] or 0),
        sales=float(agg["total_sales"] or 0),
        units=float(agg["total_units"] or 0),
    )


def _aggregate_target_reports(
    target_ids: list[int],
    profile_id: int,
    days: int,
    today: date,
) -> dict[int, dict[str, float]]:
    """查询定位组近 N 天报表，按定位组 ID 聚合。"""
    if not target_ids:
        return {}
    date_start = today - timedelta(days=days)
    qs = (
        LxSpTargetReport.objects
        .filter(
            target_id__in=target_ids,
            profile_id=profile_id,
            report_date__gte=date_start,
            report_date__lte=today,
        )
        .values("target_id")
        .annotate(
            total_impressions=Sum("impressions"),
            total_clicks=Sum("clicks"),
            total_cost=Sum("cost"),
            total_orders=Sum("orders"),
            total_sales=Sum("sales"),
            total_units=Sum("units"),
        )
    )
    result: dict[int, dict[str, float]] = {}
    for row in qs:
        result[row["target_id"]] = _build_metrics_dict(
            impressions=float(row["total_impressions"] or 0),
            clicks=float(row["total_clicks"] or 0),
            cost=float(row["total_cost"] or 0),
            orders=float(row["total_orders"] or 0),
            sales=float(row["total_sales"] or 0),
            units=float(row["total_units"] or 0),
        )
    return result


def _aggregate_keyword_reports(
    keyword_ids: list[int],
    profile_id: int,
    days: int,
    today: date,
) -> dict[int, dict[str, float]]:
    """查询关键词近 N 天报表，按关键词 ID 聚合。"""
    if not keyword_ids:
        return {}
    date_start = today - timedelta(days=days)
    qs = (
        LxSpKeywordReport.objects
        .filter(
            keyword_id__in=keyword_ids,
            profile_id=profile_id,
            report_date__gte=date_start,
            report_date__lte=today,
        )
        .values("keyword_id")
        .annotate(
            total_impressions=Sum("impressions"),
            total_clicks=Sum("clicks"),
            total_cost=Sum("cost"),
            total_orders=Sum("orders"),
            total_sales=Sum("sales"),
            total_units=Sum("units"),
        )
    )
    result: dict[int, dict[str, float]] = {}
    for row in qs:
        result[row["keyword_id"]] = _build_metrics_dict(
            impressions=float(row["total_impressions"] or 0),
            clicks=float(row["total_clicks"] or 0),
            cost=float(row["total_cost"] or 0),
            orders=float(row["total_orders"] or 0),
            sales=float(row["total_sales"] or 0),
            units=float(row["total_units"] or 0),
        )
    return result


# ============================================================
# 投放实体查询（不含报表）
# ============================================================

def _load_ad_group_bid_map(
    ad_group_ids: set[int],
    profile_id: int,
) -> dict[int, float]:
    """按广告组 ID 批量查询 default_bid（仅启用状态），返回 {ad_group_id: bid} 映射。"""
    if not ad_group_ids:
        return {}
    return {
        ag.ad_group_id: float(ag.default_bid)
        for ag in LxSpAdGroup.objects.filter(
            ad_group_id__in=list(ad_group_ids),
            profile_id=profile_id,
            state="enabled",
            default_bid__isnull=False,
        ).only("ad_group_id", "default_bid")
    }


def _get_auto_targets(
    campaign_id: int,
    profile_id: int,
    target_groups: list[str],
) -> list[dict[str, Any]]:
    """查自动广告的定位组（expression_type=auto, 状态=启用）。

    按 expression.type 过滤用户选择的定位组类型（同类商品/紧密匹配/关联商品/宽泛匹配）。
    关键词当前生效竞价 = 个体竞价 OR 广告组竞价。
    """
    if not target_groups:
        return []
    expr_values = {EXPR_TYPE_AUTO_MAP.get(tg, tg) for tg in target_groups}

    entities: list[dict[str, Any]] = []
    ad_group_ids: set[int] = set()
    for t in LxSpTarget.objects.filter(
        campaign_id=campaign_id,
        profile_id=profile_id,
        expression_type="auto",
        state="enabled",
    ):
        for item in (t.expression if isinstance(t.expression, list) else []):
            if isinstance(item, dict) and item.get("type", "") in expr_values:
                entities.append({
                    "target_id": t.target_id,
                    "bid": float(t.bid) if t.bid else None,
                    "expr_type": item.get("type", ""),
                    "ad_group_id": t.ad_group_id,
                })
                ad_group_ids.add(t.ad_group_id)
                break

    # 竞价继承：个体 bid → 广告组 default_bid；两者都为空则过滤
    ad_group_bid_map = _load_ad_group_bid_map(ad_group_ids, profile_id)
    result: list[dict[str, Any]] = []
    for e in entities:
        if e["bid"] is None:
            inherited = ad_group_bid_map.get(e["ad_group_id"])
            if inherited is None:
                continue
            e["bid"] = inherited
        result.append(e)
    return result


def _get_manual_keywords(
    campaign_id: int,
    profile_id: int,
) -> list[dict[str, Any]]:
    """查手动广告的所有开启关键词（状态=启用）。

    关键词当前生效竞价 = 个体竞价 OR 广告组竞价。
    """
    entities: list[dict[str, Any]] = []
    ad_group_ids: set[int] = set()
    for k in LxSpKeyword.objects.filter(
        campaign_id=campaign_id,
        profile_id=profile_id,
        state="enabled",
    ):
        entities.append({
            "keyword_id": k.keyword_id,
            "bid": float(k.bid) if k.bid else None,
            "ad_group_id": k.ad_group_id,
            "keyword_text": k.keyword_text,
        })
        ad_group_ids.add(k.ad_group_id)

    # 竞价继承：个体 bid → 广告组 default_bid；两者都为空则过滤
    ad_group_bid_map = _load_ad_group_bid_map(ad_group_ids, profile_id)
    result: list[dict[str, Any]] = []
    for e in entities:
        if e["bid"] is None:
            inherited = ad_group_bid_map.get(e["ad_group_id"])
            if inherited is None:
                continue
            e["bid"] = inherited
        result.append(e)
    return result


def _get_manual_product_targets(
    campaign_id: int,
    profile_id: int,
) -> list[dict[str, Any]]:
    """查手动广告的商品投放（LxSpTarget, expression_type=manual, 状态=启用）。

    关键词当前生效竞价 = 个体竞价 OR 广告组竞价。
    """
    entities: list[dict[str, Any]] = []
    ad_group_ids: set[int] = set()
    for t in LxSpTarget.objects.filter(
        campaign_id=campaign_id,
        profile_id=profile_id,
        expression_type="manual",
        state="enabled",
    ):
        entities.append({
            "target_id": t.target_id,
            "bid": float(t.bid) if t.bid else None,
            "ad_group_id": t.ad_group_id,
        })
        ad_group_ids.add(t.ad_group_id)

    # 竞价继承：个体 bid → 广告组 default_bid；两者都为空则过滤
    ad_group_bid_map = _load_ad_group_bid_map(ad_group_ids, profile_id)
    result: list[dict[str, Any]] = []
    for e in entities:
        if e["bid"] is None:
            inherited = ad_group_bid_map.get(e["ad_group_id"])
            if inherited is None:
                continue
            e["bid"] = inherited
        result.append(e)
    return result


# ============================================================
# 步骤 b：条件组评估
# ============================================================

def _check_campaign_min_days(
    campaign: LxSpCampaign,
    min_days: int,
    today: date,
) -> bool:
    """检查广告活动创建天数是否 ≥ 条件组要求的最小天数。不足则跳过。"""
    if campaign.creation_date is None:
        return False
    creation_date = _parse_creation_date(campaign.creation_date)
    if creation_date is None:
        return False
    return (today - creation_date).days >= min_days


def _evaluate_condition_set(
    condition_set: dict[str, Any],
    metrics: dict[str, float],
) -> bool:
    """评估单个条件组（委托 _shared.evaluate_condition_set）。

    组内 AND：所有条件必须全部通过。
    支持区间模式（isRange + operator2 + value2，如 10 < 花费 < 50）。
    """
    return evaluate_condition_set(condition_set, metrics)


def _check_condition_sets(
    rule: dict[str, Any],
    campaign: LxSpCampaign,
    today: date,
) -> tuple[bool, dict[str, Any] | None]:
    """检查规则的全部条件组。

    组间 AND：所有条件组都必须通过，任一组不通过则整条规则放弃。
    组内 AND：同组内所有条件必须全部满足。
    """
    condition_sets = rule.get("condition_sets", []) or []
    if not condition_sets:
        return True, None

    last_metrics: dict[str, Any] | None = None
    for cs in condition_sets:
        days = int(cs.get("days", 30) or 30)
        if not _check_campaign_min_days(campaign, days, today):
            return False, None
        metrics = _aggregate_campaign_report(
            campaign.campaign_id, campaign.profile_id, days, today,
        )
        last_metrics = metrics
        if not _evaluate_condition_set(cs, metrics):
            return False, None

    return True, last_metrics


# ============================================================
# 竞价计算
# ============================================================

def _calc_bid_from_action(
    current_bid: float,
    bid_action: dict[str, Any],
) -> float | None:
    """根据竞价操作类型计算调整后的竞价（委托 _shared.calc_adjusted_bid）。

    返回 None 表示操作类型未知（不执行）。
    """
    return calc_adjusted_bid(current_bid, bid_action)


# ============================================================
# 执行周期检查
# ============================================================

def _check_last_adjustment(
    entity_type: str,
    entity_id: int,
    campaign_id: int,
    profile_id: int,
    execution_cycle_days: int,
) -> tuple[bool, str]:
    """查该投放实体最近一次执行类型为"竞价调整"、调整状态为"成功"的记录，
    判断距今是否已满规则组的执行周期。

    逻辑：
      - 无历史成功记录 → 允许执行（首次调整）
      - 有记录 → 取调整时间，计算距今天数
        - 距今天数 < 执行周期 → 不允许（周期未到）
        - 距今天数 ≥ 执行周期 → 允许
    """
    filter_kwargs = {
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

    if last is None or last.adjustment_time is None:
        return True, "首次调整（无历史成功记录）"

    days_since = (datetime.now(dt_timezone.utc) - last.adjustment_time).days

    if days_since < execution_cycle_days:
        return False, (
            f"执行周期未到：距上次调整仅 {days_since} 天，"
            f"需 ≥ {execution_cycle_days} 天"
        )

    return True, (
        f"执行周期已满足：距上次调整 {days_since} 天，"
        f"≥ {execution_cycle_days} 天"
    )


# ============================================================
# 投放竞价操作（完整实现）
# ============================================================

def _execute_targeting_bid_item(
    tba: dict[str, Any],
    campaign: LxSpCampaign,
    group_id: int,
    today: date,
) -> dict[str, Any]:
    """对单条 targeting_bid_action 执行筛选投放实体 + 条件组 AND + 竞价计算。"""
    _ = group_id  # TODO: 从 group_id 查 LxAdRuleGroup.execution_cycle
    targeting_type = campaign.targeting_type or "auto"
    target_groups = tba.get("targetingGroups", []) or []
    unlimited = bool(tba.get("unlimitedTargeting", False))
    condition_sets = tba.get("conditionSets", []) or []
    bid_action = tba.get("bidAction") or {}

    # 当前执行周期硬编码为 1 天（后续从 LxAdRuleGroup.execution_cycle 取）

    bid_type = bid_action.get("type", "")
    if not bid_type or bid_type == "no_adjust":
        return {
            "action": "投放竞价",
            "状态": "跳过",
            "原因": "操作类型为不调整或无操作",
        }

    # ── 1. 筛选投放实体 ──
    entities: list[dict[str, Any]] = []

    if targeting_type == "auto":
        if not unlimited and not target_groups:
            return {"action": "投放竞价", "状态": "跳过", "原因": "未选择定位组类型"}
        entities = _get_auto_targets(
            campaign.campaign_id, campaign.profile_id,
            target_groups if not unlimited
            else ["close_match", "loose_match", "substitutes", "complements"],
        )
    else:
        want_keyword = unlimited or "keyword" in target_groups
        want_product = unlimited or "product_targeting" in target_groups
        if want_keyword:
            for kw in _get_manual_keywords(campaign.campaign_id, campaign.profile_id):
                entities.append({**kw, "_entity_type": "keyword"})
        if want_product:
            for pt in _get_manual_product_targets(campaign.campaign_id, campaign.profile_id):
                entities.append({**pt, "_entity_type": "product_targeting"})

    if not entities:
        return {"action": "投放竞价", "状态": "跳过", "原因": "无匹配的投放实体"}

    # ── 2. 批量查报表（取最大天数一次查完，并按条件组天数预缓存）──
    max_days = 30
    for cs in condition_sets:
        d = int(cs.get("days", 30) or 30)
        if d > max_days:
            max_days = d

    keyword_ids = [e["keyword_id"] for e in entities if e.get("_entity_type") == "keyword"]
    target_ids = [e["target_id"] for e in entities if e.get("_entity_type") != "keyword"]

    target_metrics = _aggregate_target_reports(target_ids, campaign.profile_id, max_days, today)
    keyword_metrics = _aggregate_keyword_reports(keyword_ids, campaign.profile_id, max_days, today)

    # 预缓存：条件组天数 ≠ max_days 时，避免逐实体单独查询
    _cs_metrics_cache: dict[tuple[int, str], dict[int, dict[str, float]]] = {}
    for cs in condition_sets:
        cs_days = int(cs.get("days", 30) or 30)
        if cs_days == max_days:
            continue
        cache_key_kw = (cs_days, "keyword")
        if cache_key_kw not in _cs_metrics_cache:
            _cs_metrics_cache[cache_key_kw] = _aggregate_keyword_reports(
                keyword_ids, campaign.profile_id, cs_days, today,
            )
        cache_key_tgt = (cs_days, "target")
        if cache_key_tgt not in _cs_metrics_cache:
            _cs_metrics_cache[cache_key_tgt] = _aggregate_target_reports(
                target_ids, campaign.profile_id, cs_days, today,
            )

    # ── 3. 逐实体评估 → 生成调整计划 ──
    plans: list[dict[str, Any]] = []

    for entity in entities:
        etype = entity.get("_entity_type", "定位组")
        if etype == "keyword":
            entity_id = entity["keyword_id"]
            metrics = keyword_metrics.get(entity_id)
            entity_label = f"关键词 {entity.get('keyword_text', entity_id)}"
        else:
            entity_id = entity["target_id"]
            metrics = target_metrics.get(entity_id)
            entity_label = f"定位组/商品投放 {entity_id}"

        # 无报表数据 → 视为全 0，继续条件评估与竞价比对
        if metrics is None:
            metrics = _build_metrics_dict(0, 0, 0, 0, 0, 0)

        # 条件组 AND 全通过
        conds_failed_reason = ""
        conds_passed = True
        for cs in condition_sets:
            cs_days = int(cs.get("days", 30) or 30)
            if cs_days != max_days:
                cache_key = (cs_days, "keyword" if etype == "keyword" else "target")
                filtered = _cs_metrics_cache.get(cache_key, {}).get(entity_id)
            else:
                filtered = metrics

            if not filtered or not _evaluate_condition_set(cs, filtered):
                conds_passed = False
                conds_failed_reason = f"条件组（近{cs_days}天）未通过"
                break

        if not conds_passed:
            plans.append({
                "实体类型": etype,
                "实体ID": entity_id,
                "实体名称": entity_label,
                "结果": "跳过",
                "原因": conds_failed_reason,
                "报表数据": metrics,
            })
            continue

        # 执行周期检查（当前硬编码 1 天，后续从 LxAdRuleGroup 取）
        can_exec, reason = _check_last_adjustment(
            etype, entity_id,
            campaign.campaign_id, campaign.profile_id,
            execution_cycle_days=1,
        )
        if not can_exec:
            plans.append({
                "实体类型": etype,
                "实体ID": entity_id,
                "实体名称": entity_label,
                "结果": "跳过",
                "原因": reason,
                "报表数据": metrics,
            })
            continue

        # 计算竞价
        current_bid = entity.get("bid", 0.0)
        new_bid = _calc_bid_from_action(current_bid, bid_action)

        if new_bid is None:
            plans.append({
                "实体类型": etype,
                "实体ID": entity_id,
                "实体名称": entity_label,
                "结果": "跳过",
                "原因": f"不支持的竞价操作类型: {bid_type}",
            })
            continue

        if new_bid == current_bid:
            # 调整前后竞价相同，不写表
            continue

        plans.append({
            "实体类型": etype,
            "实体ID": entity_id,
            "实体名称": entity_label,
            "结果": "待执行",
            "调整前竞价": current_bid,
            "调整后竞价": round(new_bid, 4),
            "竞价操作类型": bid_type,
            "操作参数": {
                "type": bid_type,
                "value": bid_action.get("value"),
                "limit": bid_action.get("limit"),
            },
            "执行周期检查": reason,
            "报表数据": metrics,
        })

    return {
        "action": "投放竞价",
        "状态": "完成",
        "投放对象": target_groups if not unlimited else ["全部"],
        "不限": unlimited,
        "命中实体数": sum(1 for p in plans if p["结果"] != "跳过"),
        "执行实体数": sum(1 for p in plans if p["结果"] == "待执行"),
        "明细": plans,
    }


def _execute_targeting_bid_actions(
    rule: dict[str, Any],
    campaign: LxSpCampaign,
    today: date,
) -> list[dict[str, Any]]:
    """执行规则中所有投放竞价操作。每条互不影响。"""
    tba_list = rule.get("targeting_bid_actions", []) or []
    if not tba_list:
        return []

    group_id = rule.get("group_id", 0)
    results: list[dict[str, Any]] = []
    for i, tba in enumerate(tba_list):
        try:
            result = _execute_targeting_bid_item(tba, campaign, group_id, today)
            results.append(result)
        except Exception as e:
            logger.exception("[executor_campaign] 投放竞价 %d 异常: %s", i, e)
            results.append({
                "action": "投放竞价",
                "序号": i,
                "状态": "异常",
                "错误": str(e),
            })
    return results


# ============================================================
# 预算 & 其他操作（占位）
# ============================================================

def _execute_budget_action(
    rule: dict[str, Any],
    campaign: LxSpCampaign,
) -> dict[str, Any]:
    """规则级预算操作 —— 委托 _shared。"""
    _ = campaign  # 预算操作暂时不依赖 campaign
    return _shared_execute_budget_action(rule)


def _execute_other_action(
    rule: dict[str, Any],
    campaign: LxSpCampaign,
) -> dict[str, Any]:
    """规则级暂停/归档操作 —— 委托 _shared.execute_pause_archive_action。

    广告活动维度：entity_type="campaign"，不传 entity_id。
    """
    from api_v2.models.sp_ad_pause_archive import PauseArchiveEntityType

    return execute_pause_archive_action(
        rule,
        campaign_id=campaign.campaign_id,
        profile_id=campaign.profile_id,
        entity_type=PauseArchiveEntityType.CAMPAIGN,
    )


# ============================================================
# 单条规则执行
# ============================================================

def _execute_campaign_rule(
    rule: dict[str, Any],
    campaign: LxSpCampaign,
    today: date,
) -> dict[str, Any] | None:
    """执行单条 campaign 维度规则。

    流程：
      a. 分时策略联动检查
      b. 条件组评估（组间 AND，组内 AND）
      c. 全部通过 → 执行三类操作：
         - 投放竞价（完整实现）
         - 预算操作（占位）
         - 其他操作（占位）
        然后写本地 JSON 文件（临时），返回执行结果
    """
    rule_id = rule.get("rule_id", "?")
    rule_name = rule.get("rule_name", "?")

    # a. 分时联动
    if not _check_time_pricing_link(rule, campaign.campaign_id, campaign.profile_id):
        logger.info("[executor_campaign] 规则「%s」(id=%s) 分时联动不通过 → 跳过", rule_name, rule_id)
        return None

    # b. 条件组
    passed, _ = _check_condition_sets(rule, campaign, today)
    if not passed:
        logger.info("[executor_campaign] 规则「%s」(id=%s) 条件组不通过 → 跳过", rule_name, rule_id)
        return None

    logger.info("[executor_campaign] 规则「%s」(id=%s) 条件全部通过，开始执行操作", rule_name, rule_id)

    # c. 执行竞价操作 → 写入 SpBidAdjustment
    targeting_results = _execute_targeting_bid_actions(rule, campaign, today)

    # 从每条 targeting_bid_action 的明细中提取"待执行"记录批量写表
    total_written = 0
    for tba_result in targeting_results:
        if not isinstance(tba_result, dict):
            continue
        plans = tba_result.get("明细", []) or []
        records: list[SpBidAdjustment] = []
        now = datetime.now(dt_timezone.utc)
        for p in plans:
            if p.get("结果") != "待执行":
                continue
            entity_type = p.get("实体类型", "")
            entity_id = p.get("实体ID")
            if entity_id is None:
                continue
            bid_before_val = p.get("调整前竞价")
            bid_after_val = p.get("调整后竞价")
            adj_status, exec_status, msg = resolve_adjustment_status(
                campaign.campaign_id, campaign.profile_id,
                float(bid_before_val) if bid_before_val else 0.0,
                float(bid_after_val) if bid_after_val else 0.0,
            )
            record = SpBidAdjustment(
                campaign_id=campaign.campaign_id,
                profile_id=campaign.profile_id,
                execution_type=ExecutionTypeChoices.BID_ADJUSTMENT,
                auto_rule_id=rule.get("rule_id"),
                bid_before=bid_before_val,
                bid_after=bid_after_val,
                adjustment_status=adj_status,
                execution_status=exec_status,
                msg=msg,
                adjustment_time=now,
            )
            if entity_type == "keyword":
                record.keyword_id = entity_id
            else:
                record.target_id = entity_id
            records.append(record)
        if records:
            SpBidAdjustment.objects.bulk_create(records, batch_size=500)
            # 同步更新实体表 bid
            for rec in records:
                etype = "keyword" if rec.keyword_id else "target"
                eid = rec.keyword_id or rec.target_id
                if eid:
                    apply_bid_update(etype, eid, float(rec.bid_after or 0))
            total_written += len(records)

    if total_written > 0:
        logger.info(
            "[executor_campaign] 写入 SpBidAdjustment %d 条, campaign=%d, rule=%s",
            total_written, campaign.campaign_id, rule.get("rule_id"),
        )

    budget_result = _execute_budget_action(rule, campaign)
    other_result = _execute_other_action(rule, campaign)

    return {
        "规则ID": rule_id,
        "规则名称": rule_name,
        "优先级": rule.get("priority", 0),
        "广告活动ID": campaign.campaign_id,
        "店铺ID": campaign.profile_id,
        "投放类型": campaign.targeting_type,
        "写入记录数": total_written,
        "预算操作": budget_result,
        "其他操作": other_result,
        "竞价操作": targeting_results,
    }


# ============================================================
# 规则提取
# ============================================================

def _extract_campaign_rules(
    auto_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """从 auto_rules 中提取比对对象="campaign" 的规则，按优先级升序。"""
    rules: list[dict[str, Any]] = []
    for item in auto_rules:
        if not isinstance(item, dict):
            continue
        if item.get("comparison_target") != COMPARISON_TARGET_CAMPAIGN:
            continue
        rules.extend(item.get("rules", []) or [])
    rules.sort(key=lambda r: r.get("priority", 0))
    return rules


# ============================================================
# 主入口
# ============================================================

def execute_campaign_rules() -> dict[str, Any]:
    """执行广告活动维度的优化策略规则。

    链路：
      1. 扫描 LxSpCampaign（状态=开启）
      2. 以（广告活动ID, 店铺ID, 投放类型）匹配 sp_ad_optimization_strategy
         中当日已更新且有 auto_rules 的记录
      3. 提取 campaign 维度规则，按优先级执行，命中即停
      4. 执行结果写入本地 JSON 文件（临时）

    Returns:
        {
            "扫描广告活动数": int,
            "有策略记录数": int,
            "执行规则数": int,
            "受影响广告活动数": int,
            "结果详情": list[dict],
            "错误列表": list[str],
        }
    """
    today = date.today()

    # ── 1. 扫描所有开启的广告活动 ──
    enabled = list(
        LxSpCampaign.objects.filter(state="enabled")
        .values("campaign_id", "profile_id", "targeting_type")
    )
    if not enabled:
        return {
            "扫描广告活动数": 0, "有策略记录数": 0, "执行规则数": 0,
            "受影响广告活动数": 0, "结果详情": [], "错误列表": [],
        }
    logger.info("[executor_campaign] 扫描开启广告活动: %d", len(enabled))

    # ── 2. 批量匹配策略记录 ──
    all_strategies: dict[tuple, SpAdOptimizationStrategy] = {}
    pairs = [(c["campaign_id"], c["profile_id"]) for c in enabled]
    for i in range(0, len(pairs), 500):
        q = Q()
        for cid, pid in pairs[i:i + 500]:
            q |= Q(campaign_id=cid, profile_id=pid)
        for s in SpAdOptimizationStrategy.objects.filter(
            q, rule_updated_today=True,
        ).exclude(auto_rules=[], manual_rules=[]):
            all_strategies[(s.campaign_id, s.profile_id, s.targeting_type)] = s
    logger.info("[executor_campaign] 有策略记录: %d", len(all_strategies))

    # 批量预加载所有需要访问的广告活动（避免循环内 N+1 查询）
    _campaign_qs = LxSpCampaign.objects.filter(state="enabled").only(
        "campaign_id", "profile_id", "targeting_type", "creation_date",
    )
    campaign_map: dict[tuple[int, int], LxSpCampaign] = {
        (c.campaign_id, c.profile_id): c for c in _campaign_qs
    }

    # ── 3. 遍历执行 ──
    all_results: list[dict[str, Any]] = []
    errors: list[str] = []
    executed = 0
    affected: set[tuple[int, int]] = set()

    for c in enabled:
        cid = c["campaign_id"]
        pid = c["profile_id"]
        tt = c["targeting_type"] or "auto"

        strategy = all_strategies.get((cid, pid, tt))
        if strategy is None:
            continue

        rules = _extract_campaign_rules(resolve_rules(strategy))
        if not rules:
            continue

        campaign = campaign_map.get((cid, pid))
        if campaign is None:
            continue

        for rule in rules:
            try:
                result = _execute_campaign_rule(rule, campaign, today)
            except Exception as e:
                msg = f"campaign={cid} rule={rule.get('rule_id')} 异常: {e}"
                logger.exception("[executor_campaign] %s", msg)
                errors.append(msg)
                continue
            if result is not None:
                all_results.append(result)
                executed += 1
                # 统计是否有真正的竞价变动
                tba_results = result.get("竞价操作", []) or []
                bid_effected = any(
                    isinstance(t, dict) and t.get("执行实体数", 0) > 0
                    for t in tba_results
                )
                if bid_effected:
                    affected.add((cid, pid))
                    break  # 竞价已执行，该广告活动后续规则全部跳过
                # bid_effected=False：条件通过但无竞价变动，继续尝试下一条规则

    logger.info(
        "[executor_campaign] 完成: campaign=%d, strategy=%d, executed=%d, affected=%d, errors=%d",
        len(enabled), len(all_strategies), executed, len(affected), len(errors),
    )

    return {
        "扫描广告活动数": len(enabled),
        "有策略记录数": len(all_strategies),
        "执行规则数": executed,
        "受影响广告活动数": len(affected),
        "结果详情": all_results,
        "错误列表": errors,
    }
