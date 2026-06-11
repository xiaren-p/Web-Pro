"""SP 广告优化策略——商品投放维度执行器（executor_product_targeting）。

对 auto_rules 中 comparison_target="product_targeting" 的规则执行。
数据来源：LxSpTarget（expression_type="manual"）
报表来源：LxSpTargetReport（与定位组同一张表）
"""

from __future__ import annotations
import json as _json, logging, os
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any
from django.db.models import Q, Sum

from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.basic.lx_sp_target import LxSpTarget
from api_v1.models.lingxing.ads.report.lx_sp_target_report import LxSpTargetReport
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit
from api_v2.models.sp_ad_optimization_strategy import SpAdOptimizationStrategy
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices, ExecutionTypeChoices, SpBidAdjustment,
)

logger = logging.getLogger(__name__)
_DEBUG_DIR = os.path.join(os.path.dirname(__file__), "_debug_output")
_DEFAULT_CYCLE_DAYS = 1

# ── 通用 ──
def _ensure(): os.makedirs(_DEBUG_DIR, exist_ok=True)

def _debug(fn: str, d: Any):
    p = os.path.join(_DEBUG_DIR, fn)
    with open(p, "w", encoding="utf-8") as f:
        _json.dump(d, f, ensure_ascii=False, indent=2, default=str)
    logger.info("[pt] %s", p)

# ── 指标 ──
def _metrics(i: float, c: float, cost: float, o: float, s: float, u: float) -> dict:
    return {"impressions": i, "clicks": c, "cost": cost, "spend": cost,
            "orders": o, "sales": s, "adssales": s, "units": u, "adsvolume": u,
            "cpa": cost/o if o else 0, "acos": cost/s*100 if s else 0,
            "roas": s/cost if cost else 0, "cpc": cost/c if c else 0,
            "ctr": c/i*100 if i else 0, "cvr": o/c*100 if c else 0,
            "spendspercent": 0, "adssalespercent": 0}

def _report(tid: int, pid: int, days: int, today: date) -> dict | None:
    ds = today - timedelta(days=days)
    a = LxSpTargetReport.objects.filter(target_id=tid, profile_id=pid, report_date__gte=ds, report_date__lte=today).aggregate(
        i=Sum("impressions"), c=Sum("clicks"), cost=Sum("cost"), o=Sum("orders"), s=Sum("sales"), u=Sum("units"))
    if float(a["i"] or 0) == 0 and float(a["c"] or 0) == 0 and float(a["cost"] or 0) == 0: return None
    return _metrics(float(a["i"] or 0), float(a["c"] or 0), float(a["cost"] or 0), float(a["o"] or 0), float(a["s"] or 0), float(a["u"] or 0))

# ── 分时联动 ──
def _time_link(rule: dict, cid: int, pid: int) -> bool:
    linked = rule.get("linked_time_rules") or []; exc = rule.get("linked_time_rules_exclude") or []
    if not linked and not exc: return True
    try: hit = AdTimePricingHit.objects.filter(campaign_id=cid, profile_id=pid).first()
    except Exception as e: logger.warning("[pt] 分时查询失败: %s", e, exc_info=True); return False
    ids = set(str(hit.hit_time_pricing_rules).split(",")) if (hit and hit.hit_time_pricing_rules) else set()
    if exc and ids & {str(x) for x in exc}: return False
    if linked and not (ids & {str(x) for x in linked}): return False
    return True

# ── 条件 ──
def _op(a: float, op: str, t: float) -> bool:
    if op == ">": return a > t
    if op == "<": return a < t
    if op == ">=": return a >= t
    if op == "<=": return a <= t
    if op == "==": return a == t
    if op == "!=": return a != t
    return False

def _eval_cs(cs: dict, m: dict) -> bool:
    for c in (cs.get("conditions") or []):
        a = m.get(str(c.get("metric", "")).lower())
        if a is None: return False
        if not _op(a, str(c.get("operator", ">")), float(c.get("value", 0) or 0)): return False
        if bool(c.get("isRange")):
            if not _op(a, str(c.get("operator2", "<")), float(c.get("value2", 0) or 0)): return False
    return True

def _check_all(rule: dict, m: dict | None) -> tuple[bool, str]:
    css = rule.get("condition_sets") or []
    if not css: return True, ""
    if m is None: return False, "无报表数据"
    for cs in css:
        if not _eval_cs(cs, m): return False, f"条件组（近{cs.get('days','?')}天）未通过"
    return True, ""

# ── 竞价 ──
def _bid(cur: float, ba: dict) -> float | None:
    t, v = ba.get("type", ""), float(ba.get("value", 0) or 0)
    lim = float(ba.get("limit")) if ba.get("limit") is not None else None
    if t == "bid_percent_decrease": b = cur*(1-v/100); b = max(b, lim) if lim else b; return max(b, 0.02)
    if t == "bid_percent_increase":  b = cur*(1+v/100); return min(b, lim) if lim else b
    if t == "bid_fixed_decrease":    b = cur-v; b = max(b, lim) if lim else b; return max(b, 0.02)
    if t == "bid_fixed_increase":    b = cur+v; return min(b, lim) if lim else b
    return None

# ── 执行周期 ──
def _last_time(tid: int, cid: int, pid: int) -> datetime | None:
    r = (SpBidAdjustment.objects.filter(
        campaign_id=cid, profile_id=pid, target_id=tid,
        execution_type=ExecutionTypeChoices.BID_ADJUSTMENT, adjustment_status=AdjustmentStatusChoices.SUCCESS)
        .order_by("-adjustment_time").first())
    return r.adjustment_time if (r and r.adjustment_time) else None

def _cycle_ok(lt: datetime | None, cd: int) -> tuple[bool, str]:
    if lt is None: return True, "首次"
    s = (datetime.now(dt_timezone.utc) - lt).days
    return (True, f"{s}天") if s >= cd else (False, f"周期未到({s}天<{cd}天)")

# ── 投放竞价 ──
def _tba(r: dict, pt: LxSpTarget, camp: LxSpCampaign, today: date) -> tuple[list[dict], bool]:
    tba_list = r.get("targeting_bid_actions") or []
    if not tba_list: return [], False

    md = 30
    for t in tba_list:
        for cs in (t.get("conditionSets") or []): md = max(md, int(cs.get("days", 30) or 30))
    metrics = _report(pt.target_id, camp.profile_id, md, today)
    executed = False; results = []

    for i, tb in enumerate(tba_list):
        gs = tb.get("targetingGroups") or []; unlim = bool(tb.get("unlimitedTargeting")); ba = tb.get("bidAction") or {}
        if not unlim and "product_targeting" not in gs: continue

        bt = ba.get("type", "")
        if not bt or bt == "no_adjust": results.append({"序号": i, "状态": "跳过", "原因": "无操作"}); continue

        cs_ok, cs_fail = True, ""
        for cs in (tb.get("conditionSets") or []):
            d = int(cs.get("days", 30) or 30)
            m = metrics if d == md else _report(pt.target_id, camp.profile_id, d, today)
            if not m or not _eval_cs(cs, m): cs_ok = False; cs_fail = f"投放级条件组（近{d}天）未通过"; break
        if not cs_ok: results.append({"序号": i, "状态": "跳过", "原因": cs_fail, "商品投放ID": pt.target_id, "报表": metrics}); continue

        cur = float(pt.bid) if pt.bid else 0
        nb = _bid(cur, ba)
        if nb is None: results.append({"序号": i, "状态": "跳过", "原因": f"不支持: {bt}"}); continue
        if nb == cur: results.append({"序号": i, "状态": "无需调整", "商品投放ID": pt.target_id, "竞价": cur}); continue

        executed = True
        results.append({"序号": i, "状态": "待执行", "商品投放ID": pt.target_id,
                        "调整前": cur, "调整后": round(nb, 4), "操作": bt,
                        "参数": {"type": bt, "value": ba.get("value"), "limit": ba.get("limit")}, "报表": metrics})

    return results, executed

# ── 预算/其他（占位） ──
def _budget(r: dict) -> dict:
    ba = r.get("budget_action") or {}; t = (ba or {}).get("type", "") if isinstance(ba, dict) else ""
    return {"操作": "预算", "状态": "跳过"} if (not t or t == "no_adjust") else {"操作": "预算", "状态": "占位", "类型": t}

def _other(r: dict) -> dict:
    oa = r.get("other_action") or {}; t = (oa or {}).get("type", "") if isinstance(oa, dict) else ""
    return {"操作": "其他", "状态": "跳过"} if (not t or t == "no_other") else {"操作": "其他", "状态": "占位", "类型": t}

# ── 单条规则 ──
def _rule(rule: dict, pt: LxSpTarget, camp: LxSpCampaign, today: date) -> tuple[dict | None, bool]:
    rid, rname = rule.get("rule_id", "?"), rule.get("rule_name", "?")
    if not _time_link(rule, camp.campaign_id, camp.profile_id): return None, False
    md = 30
    for cs in (rule.get("condition_sets") or []): md = max(md, int(cs.get("days", 30) or 30))
    m = _report(pt.target_id, camp.profile_id, md, today)
    ok, reason = _check_all(rule, m)
    if not ok: logger.info("[pt] rule「%s」pt=%d 条件不通过: %s", rname, pt.target_id, reason); return None, False
    tb_results, bid_done = _tba(rule, pt, camp, today)
    res = {"规则ID": rid, "规则名称": rname, "优先级": rule.get("priority", 0),
           "广告活动ID": camp.campaign_id, "店铺ID": camp.profile_id,
           "商品投放ID": pt.target_id, "当前竞价": float(pt.bid) if pt.bid else 0, "报表": m,
           "预算": _budget(rule), "其他": _other(rule), "投放竞价": tb_results}
    _debug(f"pt_{pt.target_id}_{rid}.json", res); return res, bid_done

# ── 提取 ──
def _extract(ar: list) -> list[dict]:
    rules = []
    for it in ar:
        if isinstance(it, dict) and it.get("comparison_target") == "product_targeting": rules.extend(it.get("rules") or [])
    rules.sort(key=lambda r: r.get("priority", 0)); return rules

# ═══════════════ 主入口 ═══════════════
def execute_product_targeting_rules() -> dict[str, Any]:
    """
    优化策略——商品投放维度执行。前置周期跳过 + 竞价全局互斥。
    数据来源：LxSpTarget（expression_type=manual）。
    """
    today = date.today(); _ensure()

    # ── 1. 扫描 ──
    pts = list(LxSpTarget.objects.filter(expression_type="manual", state="enabled", bid__isnull=False)
               .only("campaign_id", "profile_id", "target_id", "bid", "ad_group_id", "expression"))
    if not pts: return {"扫描": 0, "周期跳过": 0, "有策略": 0, "执行规则": 0, "受影响": 0, "详情": [], "错误": []}
    logger.info("[pt] 扫描: %d", len(pts))

    # ── 2. 前置周期跳过 ──
    cycle_skip = 0; active = []
    for t in pts:
        lt = _last_time(t.target_id, t.campaign_id, t.profile_id)
        ok, _ = _cycle_ok(lt, _DEFAULT_CYCLE_DAYS)
        if not ok: cycle_skip += 1
        else: active.append(t)
    logger.info("[pt] 周期跳过: %d, 进入: %d", cycle_skip, len(active))
    if not active: return {"扫描": len(pts), "周期跳过": cycle_skip, "有策略": 0, "执行规则": 0, "受影响": 0, "详情": [], "错误": []}

    # ── 3. 批量加载 ──
    pairs = list({(t.campaign_id, t.profile_id) for t in active})
    sm: dict[tuple, SpAdOptimizationStrategy] = {}; cm: dict[tuple, LxSpCampaign] = {}
    for i in range(0, len(pairs), 500):
        q = Q(); [q.__or__(Q(campaign_id=cid, profile_id=pid)) for cid, pid in pairs[i:i+500]]
        for s in SpAdOptimizationStrategy.objects.filter(q, rule_updated_today=True, targeting_type="manual").exclude(auto_rules=[]):
            sm[(s.campaign_id, s.profile_id, s.targeting_type)] = s
        for c in LxSpCampaign.objects.filter(q, state="enabled"): cm[(c.campaign_id, c.profile_id)] = c
    logger.info("[pt] 有策略: %d", len(sm))

    # ── 4. 遍历执行 ──
    results, errors, executed, affected = [], [], 0, set()
    for t in active:
        camp = cm.get((t.campaign_id, t.profile_id))
        if not camp: continue
        strat = sm.get((t.campaign_id, t.profile_id, "manual"))
        if not strat: continue
        rules = _extract(strat.auto_rules)
        if not rules: continue

        bid_already_done = False
        for rule in rules:
            if bid_already_done:
                logger.info("[pt] pt=%d 已有竞价, 跳过规则「%s」", t.target_id, rule.get("rule_name", "?")); continue
            try:
                res, bid_done = _rule(rule, t, camp, today)
            except Exception as e:
                msg = f"pt={t.target_id} rule={rule.get('rule_id')} {e}"; logger.exception("[pt] %s", msg); errors.append(msg); continue
            if res is not None:
                results.append(res); executed += 1; affected.add(t.target_id)
                if bid_done: bid_already_done = True
                break

    logger.info("[pt] done: active=%d executed=%d affected=%d", len(active), executed, len(affected))
    return {"扫描": len(pts), "周期跳过": cycle_skip, "有策略": len(sm), "执行规则": executed, "受影响": len(affected), "详情": results, "错误": errors}
