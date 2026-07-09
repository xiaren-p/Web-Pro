"""SP 竞价调整记录查询选择器。

提供关键词/定位组最近一次竞价调整的星标信息构建逻辑。
``keyword_view`` 与 ``auto_targeting_view`` 共用此选择器，消除 ~230 行重复代码。
"""
import logging
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Max
from django.utils import timezone

from apps.ads.models.lx_ads_profile import LxAdsProfile
from apps.ads.sp.rules.models.lx_ad_rule import LxAdRule
from apps.ads.sp.rules.models.sp_bid_adjustment import (
    SpBidAdjustment,
    ExecutionTypeChoices as BidExecType,
)
from apps.common.utils.timezone_utils import country_to_timezone

logger = logging.getLogger(__name__)


def build_bid_latest_adjustment_map(
    entity_ids: list[str],
    entity_field: str,
    profile_id: int,
    types: set | None = None,
) -> dict[str, dict[str, Any]]:
    """构建投放实体最近修改星标信息（性能优化版：用 MAX(id) 子查询取每实体最新记录）。

    Args:
        entity_ids: 实体 ID 列表。
        entity_field: "keyword_id" 或 "target_id"。
        profile_id: 店铺 Profile ID。
        types: 可选，限制只查这些 execution_type；None 表示全部。

    Returns:
        dict[str, dict[str, Any]]: 实体 ID → {has_recent, lines}。
    """
    if not entity_ids:
        return {}

    int_ids = [int(x) for x in entity_ids if x]
    if not int_ids:
        return {}

    threshold = timezone.now() - timedelta(days=7)
    filter_kwargs: dict[str, Any] = {
        f"{entity_field}__in": int_ids, "created_at__gte": threshold,
    }
    if types:
        filter_kwargs["execution_type__in"] = list(types)
    base_qs = SpBidAdjustment.objects.filter(
        **filter_kwargs,
    ).only("id", entity_field, "execution_type", "auto_rule_id", "operator", "bid_before", "bid_after", "created_at")

    latest_ids = base_qs.values(entity_field).annotate(max_id=Max("id")).values_list("max_id", flat=True)
    records = list(SpBidAdjustment.objects.filter(id__in=list(latest_ids)).only(
        "id", entity_field, "execution_type", "auto_rule_id", "operator", "bid_before", "bid_after", "created_at",
    ))

    if not records:
        return {}

    rule_ids = {r.auto_rule_id for r in records if r.auto_rule_id}
    rule_map: dict[int, Any] = {}
    if rule_ids:
        for rule in LxAdRule.objects.filter(id__in=rule_ids).only("id", "name", "condition_sets"):
            rule_map[rule.id] = rule

    tz_name, country_name = "", ""
    prof = LxAdsProfile.objects.filter(profile_id=profile_id).only("country_code", "sid").first()
    if prof:
        tz_name = country_to_timezone(prof.country_code or "")
        from apps.sales.models.lx_shops import LxShops
        country_name = LxShops.objects.filter(sid=prof.sid).values_list("country", flat=True).first() or (prof.country_code or "")

    result: dict[str, dict[str, Any]] = {}
    for rec in records:
        eid = getattr(rec, entity_field, None) or rec.keyword_id or rec.target_id
        if eid is not None:
            lines = build_bid_lines(rec, rule_map, country_name, tz_name)
            result[str(eid)] = {"has_recent": True, "lines": lines}
    return result


def build_bid_lines(
    rec: Any,
    rule_map: dict[int, Any],
    country_name: str,
    tz_name: str,
) -> list[str]:
    """按 execution_type 构建多行展示文案。

    Args:
        rec: 竞价调整记录（SpBidAdjustment 实例）。
        rule_map (dict[int, Any]): 规则 ID → 规则对象映射。
        country_name (str): 国家名称（用于时间展示）。
        tz_name (str): 时区名称（IANA 标识）。

    Returns:
        list[str]: 可读说明行列表。
    """
    is_rule = bool(rec.auto_rule_id)
    rule = rule_map.get(rec.auto_rule_id) if is_rule else None
    rule_name = getattr(rule, "name", "") if rule else "未知规则"
    operator = rec.operator or "未知用户"
    etype = rec.execution_type

    if is_rule:
        line1 = f"最近一次修改通过「{rule_name}」规则修改"
    else:
        line1 = f"最近一次修改由{operator}完成"

    local_time_str = country_name + "时间: 未知"
    if rec.created_at:
        try:
            if tz_name:
                tz = ZoneInfo(tz_name)
                local_dt = rec.created_at.astimezone(tz)
                local_time_str = f"{country_name or '当地'}时间: {local_dt.strftime('%Y-%m-%d %H:%M')}"
            else:
                local_time_str = f"{country_name or '当地'}时间: {rec.created_at.strftime('%Y-%m-%d %H:%M')}"
        except (ZoneInfoNotFoundError, Exception):
            logger.warning("[build_bid_lines] 时区转换失败，降级为 UTC 时间格式", exc_info=True)
            try:
                local_time_str = f"{country_name or '当地'}时间: {rec.created_at.strftime('%Y-%m-%d %H:%M')}"
            except Exception:
                logger.warning("[build_bid_lines] UTC 时间格式化失败", exc_info=True)

    lines = [line1, local_time_str]

    if is_rule and rule:
        try:
            cs = rule.condition_sets
            if isinstance(cs, list) and cs:
                field_label = {"cost":"花费","sales":"广告销售额","same_sales":"直接销售额","orders":"广告订单","same_orders":"直接订单","units":"广告销量","clicks":"点击","impressions":"曝光量","ctr":"CTR","cpc":"CPC","cpa":"CPA","acos":"ACoS","roas":"ROAS","cvr":"CVR","spend_rate":"花费占比","sales_rate":"销售额占比","is_ratio":"IS"}
                op_label = {">":">","<":"<",">=":"≥","<=":"≤","==":"=","!=":"≠"}
                group_parts = []
                for cg in cs:
                    if not isinstance(cg, dict): continue
                    days = cg.get("days", "?")
                    conds = cg.get("conditions") or []
                    if not isinstance(conds, list) or not conds: continue
                    cond_strs = []
                    for c in conds:
                        if not isinstance(c, dict): continue
                        m = str(c.get("metric") or c.get("field") or "")
                        o = str(c.get("operator", ">"))
                        v = c.get("value", "")
                        nm = field_label.get(m.lower(), m or "未知")
                        osym = op_label.get(o, o)
                        seg = f"{nm} {osym} {v}"
                        if bool(c.get("isRange", False)):
                            o2 = str(c.get("operator2", "<"))
                            v2 = c.get("value2", "")
                            o2sym = op_label.get(o2, o2)
                            seg = f"{v} {o2sym} {nm} {osym} {v2}"
                        cond_strs.append(seg)
                    if cond_strs:
                        group_parts.append(f"近{days}天: {', '.join(cond_strs)}")
                if group_parts:
                    lines.append(f"详细内容: {'；'.join(group_parts)}")
        except Exception:
            logger.warning("[build_bid_lines] 规则条件解析失败", exc_info=True)

    if etype == BidExecType.BID_PAUSE:
        lines.append("执行操作: 竞价暂停")
    elif etype == BidExecType.BID_ENABLE:
        lines.append("执行操作: 竞价启用")
    elif etype in (BidExecType.BID_ADJUSTMENT, BidExecType.MANUAL_ADJUSTMENT):
        before = float(rec.bid_before) if rec.bid_before is not None else 0
        after = float(rec.bid_after) if rec.bid_after is not None else 0
        lines.append(f"执行操作: 竞价 {before:.2f} → {after:.2f}")
    elif etype == BidExecType.TIME_PRICING_START:
        lines.append("执行操作: 分时开始")
    elif etype == BidExecType.TIME_PRICING_CALLBACK:
        lines.append("执行操作: 分时回调")

    return lines
