"""分时策略匹配器（strategy_matcher）。

提供统一的分时策略命中判断逻辑，供分时命中任务、自动竞价规则等模块复用。

三大匹配规则：
  1. 适用店铺：profile_id 是否在策略 shops 列表内
  2. 生效时间：当前日期是否在策略月日范围内（全 null=不限）
  3. 字段设置：产品归类/标签/负责人是否命中策略 field_settings
"""
from __future__ import annotations

from datetime import date
from typing import Any

from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy


# ============================================================
# 规则 2：时间匹配
# ============================================================

def check_time_match(strategy: LxTimePricingStrategy) -> bool:
    """检查当前日期是否在策略生效时间范围内。

    策略的 start_month/day / end_month/day 为 null 表示不限。
    年份不限——仅比较月日，因此策略每年此时段生效。

    Args:
        strategy: 分时调价策略实例

    Returns:
        True 表示当前时间在有效范围内（或策略不限时间）
    """
    today = date.today()
    sm = strategy.start_month
    sd = strategy.start_day
    em = strategy.end_month
    ed = strategy.end_day

    # 四者均为 null → 不限时间，始终命中
    if sm is None and sd is None and em is None and ed is None:
        return True

    # 四者必须全部非空才进行范围判断，部分为空属于无效配置
    if sm is None or sd is None or em is None or ed is None:
        return False

    today_md = (today.month, today.day)
    start_md = (sm, sd)
    end_md = (em, ed)

    # 跨年情况（如 11月1日 ~ 3月1日）
    if start_md <= end_md:
        return start_md <= today_md <= end_md
    return today_md >= start_md or today_md <= end_md


# ============================================================
# 规则 3：字段匹配
# ============================================================

def check_field_match(
    strategy: LxTimePricingStrategy,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
) -> bool:
    """检查产品信息是否匹配策略的字段设置。

    策略的 categories / managers / tags 若为空或全选 → 视为不限。
    只要策略中有一个值与产品匹配即可。

    Args:
        strategy: 分时调价策略实例
        product_assorts: 产品归类列表（已扁平去重）
        product_labels: 产品标签列表（已扁平去重）
        product_uids: 产品负责人 uid 列表（已扁平去重）

    Returns:
        True 表示产品字段命中策略
    """
    fs = strategy.field_settings or {}

    # 归类匹配
    strat_cats: list[str] = fs.get("categories", []) or []
    if strat_cats:
        if not any(c in strat_cats for c in product_assorts):
            return False

    # 标签匹配
    strat_tags: list[str] = fs.get("tags", []) or []
    if strat_tags:
        if not any(t in strat_tags for t in product_labels):
            return False

    # 负责人匹配（uid 对比）
    strat_managers: list[int] = [int(m) for m in (fs.get("managers", []) or []) if m]
    if strat_managers:
        if not any(uid in strat_managers for uid in product_uids):
            return False

    return True


# ============================================================
# 组合匹配：三大规则串联
# ============================================================

def match_strategy_against_product(
    profile_id: int,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
    strategies: list[LxTimePricingStrategy],
) -> dict[str, Any] | None:
    """在预加载的策略列表中匹配，返回首个命中的策略。

    按 strategies 顺序遍历（调用方应保证已按权重升序排列）。
    三条规则全部命中即返回，只命中一个。

    Args:
        profile_id: 店铺 Profile ID
        product_assorts: 产品归类列表
        product_labels: 产品标签列表
        product_uids: 产品负责人 uid 列表
        strategies: 预加载的策略列表（已按优先级排序）

    Returns:
        {"strategy_id": int, "strategy_name": str} 或 None
    """
    for s in strategies:
        # 规则 1：适用店铺
        shop_list: list = s.shops or []
        if shop_list and profile_id not in shop_list:
            continue

        # 规则 2：生效时间
        if not check_time_match(s):
            continue

        # 规则 3：字段设置
        if not check_field_match(s, product_assorts, product_labels, product_uids):
            continue

        return {
            "strategy_id": s.id,
            "strategy_name": s.name,
        }

    return None
