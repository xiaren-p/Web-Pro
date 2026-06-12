"""SP 广告优化策略——规则匹配器（campaign_rule_matcher）。

对单个 LxSpCampaign 执行 LxAdRule 的五步串联匹配，返回按比对对象分组的扁平化 auto_rules。

五步匹配规则：
  ① 适用店铺：rule.shops 为空即不限，否则 profile_id 必须在 shops 中
  ② 广告类型：ad_type（all/auto/manual）必须兼容 campaign 的 targeting_type
  ③ 生效周期：以 campaign 创建时间为基准，支持 within_days / beyond_days / date_range
  ④ 比对对象兼容：手动广告不能命中定位组规则，自动广告不能命中关键词/商品规则
  ⑤ 字段设置：归类/负责人/标签/自动定位组 的交集匹配

匹配结果按 comparison_target 分 item 后扁平化，同一 item 内规则按全局优先级升序。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from api_v1.models.lingxing.ads.lx_ad_rule import (
    ComparisonTarget,
    EffectiveType,
    LxAdRule,
)
from api_v1.models.lingxing.ads.lx_ad_rule_group import LxAdRuleGroup


# 前端 targetGroup 值 → LxSpTarget.expression.type 数据库值
_EXPR_TYPE_AUTO_MAP = {
    "close_match": "closeMatch",
    "loose_match": "looseMatch",
    "substitutes": "substitutes",
    "complements": "complements",
}


# ============================================================
# 步骤①：适用店铺匹配
# ============================================================

def _check_shop_match(rule: LxAdRule, profile_id: int) -> bool:
    """rule.shops 为空列表时视为不限（始终命中）。

    Args:
        rule: 广告规则实例
        profile_id: 店铺 Profile ID

    Returns:
        True 表示命中
    """
    shop_list: list = rule.shops or []
    if not shop_list:
        return True
    # shops 列中存储的是字符串格式的 profile_id，需统一为字符串做精确匹配
    return str(profile_id) in (str(s) for s in shop_list)


# ============================================================
# 步骤②：广告类型匹配
# ============================================================

def _check_ad_type_match(rule: LxAdRule, targeting_type: str) -> bool:
    """ad_type="all" 不限；"auto" 仅匹配 targeting_type="auto"；"manual" 仅匹配 "manual"。

    Args:
        rule: 广告规则实例
        targeting_type: campaign 的投放类型（auto / manual）

    Returns:
        True 表示命中
    """
    if rule.ad_type == "all" or not rule.ad_type:
        return True
    return rule.ad_type == targeting_type


# ============================================================
# 步骤③：生效周期匹配
# ============================================================

def _check_effective_period(
    rule: LxAdRule,
    creation_date: date | None,
    today: date,
) -> bool:
    """以 campaign.creation_date 为基准计算时间窗口。

    - within_days：今日 ∈ [creation_date + start_days, creation_date + end_days]
    - beyond_days：今日 > creation_date + start_days（不含），单值
    - date_range：今日月日在 [start_month/day, end_month/day] 范围内（年无关，跨年兼容）

    Args:
        rule: 广告规则实例
        creation_date: campaign 的创建日期（可空）
        today: 今天日期

    Returns:
        True 表示命中
    """
    effective_type = rule.effective_type

    if effective_type == EffectiveType.WITHIN_DAYS:
        start = rule.effective_days_start
        end = rule.effective_days_end
        # 天数字段均未配置 → 视为不限时间（始终命中）
        if start is None and end is None:
            return True
        # 已配置天数但 creation_date 缺失或参数不完整 → 无法计算窗口，跳过
        if creation_date is None or start is None or end is None:
            return False
        window_start = creation_date + timedelta(days=start)
        window_end = creation_date + timedelta(days=end)
        return window_start <= today <= window_end

    if effective_type == EffectiveType.BEYOND_DAYS:
        start = rule.effective_days_start
        # 天数字段未配置 → 视为不限时间（始终命中）
        if start is None:
            return True
        # 已配置天数但 creation_date 缺失 → 无法计算阈值，跳过
        if creation_date is None:
            return False
        threshold = creation_date + timedelta(days=start)
        return today > threshold

    if effective_type == EffectiveType.DATE_RANGE:
        sm = rule.effective_start_month
        sd = rule.effective_start_day
        em = rule.effective_end_month
        ed = rule.effective_end_day
        # 四者均未设置 → 视为不限
        if sm is None and sd is None and em is None and ed is None:
            return True
        # 部分为空则视为无效配置
        if sm is None or sd is None or em is None or ed is None:
            return False

        today_md = (today.month, today.day)
        start_md = (sm, sd)
        end_md = (em, ed)

        if start_md <= end_md:
            return start_md <= today_md <= end_md
        # 跨年范围（如 11/1 → 3/1）
        return today_md >= start_md or today_md <= end_md

    return False


# ============================================================
# 步骤④：比对对象兼容性校验
# ============================================================

def _check_comparison_target_compatibility(
    rule: LxAdRule,
    targeting_type: str,
) -> bool:
    """检查规则的比对对象是否与 campaign 投放类型兼容。

    - manual campaign 不能命中 comparison_target="targeting"（手动广告无定位组）
    - auto campaign 不能命中 keyword 或 product_targeting（自动广告无关键词/商品投放）
    - targeting 多选子项需至少有一个兼容项

    Args:
        rule: 广告规则实例
        targeting_type: campaign 的投放类型

    Returns:
        True 表示兼容
    """
    target = rule.comparison_target

    # manual campaign 禁止 comparison_target="targeting"
    if targeting_type == "manual" and target == ComparisonTarget.TARGETING:
        return False

    # auto campaign 禁止比较对象为关键词/商品投放
    if targeting_type == "auto" and target in (
        ComparisonTarget.KEYWORD,
        ComparisonTarget.PRODUCT_TARGETING,
    ):
        return False

    # targeting 多选子项兼容性
    if target == ComparisonTarget.TARGETING:
        multi = rule.comparison_multi_targets or []
        if not multi:
            return True  # 无多选则不限
        if targeting_type == "auto":
            # auto 仅兼容 "targeting"，排除 keyword / product_targeting
            compatible = [
                t for t in multi
                if t not in (ComparisonTarget.KEYWORD.value, ComparisonTarget.PRODUCT_TARGETING.value)
            ]
            return len(compatible) > 0
        if targeting_type == "manual":
            # manual 兼容 keyword / product_targeting，排除 "targeting"
            compatible = [
                t for t in multi
                if t != ComparisonTarget.TARGETING.value
            ]
            return len(compatible) > 0

    return True


# ============================================================
# 步骤⑤：字段设置匹配
# ============================================================

def _check_field_match(
    rule: LxAdRule,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
    auto_targeting_groups: list[str],
) -> bool:
    """检查产品字段是否命中规则的字段设置。

    四个维度（归类/负责人/标签/自动定位组），每个维度若 unlimited 为 True
    或对应列表为空则该维度不限。交集匹配：规则的限定值 ∩ 产品实际字段有交集即命中。

    Args:
        rule: 广告规则实例
        product_assorts: 产品归类列表（已扁平去重）
        product_labels: 产品标签列表（已扁平去重）
        product_uids: 产品负责人 uid 列表（已扁平去重）
        auto_targeting_groups: campaign 的自动定位组列表（DB 值）

    Returns:
        True 表示字段命中
    """
    # 归类匹配
    if not rule.unlimited_categories:
        rule_cats: list[str] = rule.categories or []
        if rule_cats:
            if not any(c in rule_cats for c in product_assorts):
                return False

    # 负责人匹配
    if not rule.unlimited_managers:
        rule_managers: list[int] = [
            int(m) for m in (rule.managers or []) if m
        ]
        if rule_managers:
            if not any(uid in rule_managers for uid in product_uids):
                return False

    # 标签匹配
    if not rule.unlimited_tags:
        rule_tags: list[str] = rule.tags or []
        if rule_tags:
            if not any(t in rule_tags for t in product_labels):
                return False

    # 自动定位组匹配：rule 中的值是前端值（close_match 等），需映射为 DB 值做交集
    if not rule.unlimited_auto_targeting:
        rule_atgs: list[str] = rule.auto_targeting_groups or []
        if rule_atgs:
            atg_mapped = {
                _EXPR_TYPE_AUTO_MAP.get(tg, tg)
                for tg in rule_atgs
            }
            if not any(tg in atg_mapped for tg in auto_targeting_groups):
                return False

    return True


# ============================================================
# 规则序列化
# ============================================================

def _serialize_rule(
    rule: LxAdRule,
    priority: int,
) -> dict[str, Any]:
    """将 LxAdRule 实例序列化为 auto_rules 规则 JSON 对象。

    Args:
        rule: 广告规则实例
        priority: 优先级值（数字越小越优先）

    Returns:
        规则的 JSON 字典
    """
    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "group_id": rule._group_id,
        "group_name": rule._group_name,
        "priority": priority,
        "comparison_target": rule.comparison_target,
        "condition_sets": rule.condition_sets,
        "bid_action": rule.bid_action,
        "budget_action": rule.budget_action,
        "other_action": rule.other_action,
        "targeting_bid_actions": rule.targeting_bid_actions,
        "negative_action": rule.negative_action,
        "add_keyword_action": rule.add_keyword_action,
        "add_keyword_match_type": rule.add_keyword_match_type,
        "add_keyword_bid_type": rule.add_keyword_bid_type,
        "add_keyword_max_bid": (
            str(rule.add_keyword_max_bid) if rule.add_keyword_max_bid is not None else None
        ),
        "add_keyword_fixed_bid": (
            str(rule.add_keyword_fixed_bid) if rule.add_keyword_fixed_bid is not None else None
        ),
    }


# ============================================================
# 优先级计算
# ============================================================

# 规则组权重因子：group.weight × 1000 + rule_index = 全局优先级，数字越小优先级越高
GROUP_WEIGHT_MULTIPLIER = 1000


def _calc_priority(group_weight: int, rule_index: int) -> int:
    """根据规则组权重和组内序号计算单条规则的全局优先级。

    公式：group_weight * 1000 + rule_index。
    rule_index 为 0-based 组内顺序号（rule_order 中的位置）。

    Args:
        group_weight: 规则组权重（0–999，数字越小优先级越高）
        rule_index: 组内规则序号（0-based，0 优先级最高）

    Returns:
        全局优先级整数
    """
    return group_weight * GROUP_WEIGHT_MULTIPLIER + rule_index


# ============================================================
# 主入口
# ============================================================

def match_rules_for_campaign(
    profile_id: int,
    targeting_type: str,
    campaign_creation_date: date | None,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
    auto_targeting_groups: list[str],
    rules_by_group: list[tuple[LxAdRuleGroup, list[LxAdRule]]],
    today: date,
) -> list[dict[str, Any]]:
    """对单个 campaign 执行五步串联匹配，返回按比对对象分组的扁平化 auto_rules。

    Args:
        profile_id: 店铺 Profile ID
        targeting_type: campaign 的投放类型（auto / manual）
        campaign_creation_date: campaign 的创建日期（可为 None）
        product_assorts: 产品归类列表
        product_labels: 产品标签列表
        product_uids: 产品负责人 uid 列表
        auto_targeting_groups: campaign 的自动定位组列表
        rules_by_group: 预加载的（规则组, [规则列表]）序列
        today: 今天日期

    Returns:
        auto_rules JSON 结构，按 comparison_target 分 item：
        [
            {"comparison_target": "campaign", "rules": [{...}, ...]},
            {"comparison_target": "keyword", "rules": [{...}, ...]},
        ]
    """
    # 收集全部命中规则（扁平列表）
    matched_rules: list[dict[str, Any]] = []

    for group, rules in rules_by_group:
        for idx, rule in enumerate(rules):
            # 步骤①：适用店铺
            if not _check_shop_match(rule, profile_id):
                continue
            # 步骤②：广告类型
            if not _check_ad_type_match(rule, targeting_type):
                continue
            # 步骤③：生效周期
            if not _check_effective_period(rule, campaign_creation_date, today):
                continue
            # 步骤④：比对对象兼容
            if not _check_comparison_target_compatibility(rule, targeting_type):
                continue
            # 步骤⑤：字段设置
            if not _check_field_match(
                rule, product_assorts, product_labels, product_uids, auto_targeting_groups,
            ):
                continue

            # 临时标注归属组信息（供序列化使用）
            rule._group_id = group.id
            rule._group_name = group.name

            # 计算优先级并序列化
            matched_rules.append(_serialize_rule(rule, _calc_priority(group.weight, idx)))

    # 按 comparison_target 分组
    if not matched_rules:
        return []

    from collections import OrderedDict
    target_map: dict[str, list[dict[str, Any]]] = OrderedDict()
    for r in matched_rules:
        target_map.setdefault(r["comparison_target"], []).append(r)

    # 输出：每个 comparison_target 一个 item，内部规则按优先级升序
    result: list[dict[str, Any]] = []
    for ct, rules in target_map.items():
        rules.sort(key=lambda r: r["priority"])
        result.append({"comparison_target": ct, "rules": rules})

    return result
