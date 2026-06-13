"""广告视图共用辅助：枚举标签映射、复合键构造、货币格式化。

仅供 ``api_v1.views.lingxing.ads`` 包内 ViewSet 复用。跨包的业务计算请放入
``api_v1.services``。

所有枚举值 → 中文 label 的映射统一集中于此文件，前端不做任何映射。
"""
from __future__ import annotations

from typing import Any

from django.db.models import Q

# ── 枚举值 → 中文 label 映射（统一出口，前端不做映射）──

# 国家代码 → 中文名称
COUNTRY_MAP: dict[str, str] = {
    "FR": "法国", "IT": "意大利", "BE": "比利时", "UK": "英国",
    "PL": "波兰", "NL": "荷兰", "SE": "瑞典", "ES": "西班牙",
    "DE": "德国", "US": "美国", "CA": "加拿大", "JP": "日本",
    "MX": "墨西哥", "AU": "澳大利亚", "SG": "新加坡", "TR": "土耳其",
    "IN": "印度", "AE": "阿联酋", "SA": "沙特", "BR": "巴西",
}

# 竞价策略 label（bidding.strategy → 中文），shop_profile_view 与 Filters.vue 共用
BIDDING_STRATEGY_LABEL: dict[str, str] = {
    "legacyForSales": "动态竞价-只降低",
    "autoForSales": "动态竞价-提高和降低",
    "manual": "固定竞价",
    "ruleBased": "基于规则的竞价",
}

# 广告活动类型简写映射（campaign_type / sponsored_type → 前端展示简写）
CAMPAIGN_TYPE_SHORT: dict[str, str] = {
    "sponsoredProducts": "SP",
    "sponsoredBrands": "SB",
    "sponsoredDisplay": "SD",
}

# 否定关键词匹配方式 label（negative_match_type → 中文）
NEGATIVE_MATCH_TYPE_LABEL: dict[str, str] = {
    "negativeExact": "否定精准",
    "negativePhrase": "否定词组",
}

# 关键词匹配类型 label（exact / broad / phrase → 中文）
KEYWORD_MATCH_TYPE_LABEL: dict[str, str] = {
    "exact": "精准匹配",
    "broad": "广泛匹配",
    "phrase": "词组匹配",
}

# 否定类型 label（negativeAsin / negativeBrand → 中文）
NEGATIVE_TYPE_LABEL: dict[str, str] = {
    "negativeAsin": "否定ASIN",
    "negativeBrand": "否定品牌",
}

# 服务状态 label（serving_status 原始枚举值 → 中文展示文字 + 前端徽标类型）
# 注：广告活动/广告组/广告投放/否定投放等所有广告实体共用同一套服务状态枚举。
# view 层通过 resolve_service_status() 统一获取 {label, type}，此处仅提供纯 label 映射供参考。
SERVICE_STATUS_LABEL: dict[str, str] = {
    "CAMPAIGN_STATUS_ENABLED": "投放中",
    "CAMPAIGN_PAUSED": "广告活动已暂停",
    "CAMPAIGN_ARCHIVED": "广告活动已归档",
    "CAMPAIGN_OUT_OF_BUDGET": "超预算",
    "CAMPAIGN_INCOMPLETE": "不完整",
    "ADVERTISER_PAYMENT_FAILURE": "广告账号付款失败",
    "LANDING_PAGE_NOT_AVAILABLE": "着陆页失效",
    "PORTFOLIO_OUT_OF_BUDGET": "超预算",
    "AD_GROUP_STATUS_ENABLED": "投放中",
    "AD_GROUP_PAUSED": "广告组已暂停",
    "AD_GROUP_STATUS_PAUSED": "广告组已暂停",
    "AD_GROUP_ARCHIVED": "广告组已归档",
    "AD_STATUS_LIVE": "投放中",
    "AD_PAUSED": "广告已暂停",
    "NOT_BUYABLE": "商品不可售",
    "MISSING_DECORATION": "素材缺失",
    "INELIGIBLE": "不符合资格",
    "AD_POLICING_SUSPENDED": "违规暂停",
    "AD_POLICING_PENDING_REVIEW": "广告审核中",
    "TARGETING_CLAUSE_STATUS_LIVE": "投放中",
    "TARGETING_CLAUSE_PAUSED": "已暂停",
    "TARGETING_CLAUSE_STATUS_PAUSED": "已暂停",
    "TARGETING_CLAUSE_ARCHIVED": "已归档",
    "TARGETING_CLAUSE_STATUS_ARCHIVED": "已归档",
    "TARGETING_CLAUSE_INCOMPLETE": "不完整",
    "OTHER": "未知",
}

# 货币查询失败时的安全 fallback
FALLBACK_CCY: dict[str, Any] = {"icon": "?", "code": "???", "rate": 1.0}


def parse_exchange_rate(my_rate_str: str | None, rate_org_str: str | None) -> float:
    """解析汇率值，优先使用用户自定义汇率（my_rate），回退到官方汇率（rate_org）。

    数据库中 ``my_rate`` 的默认值为 ``"1.0000"``（非空），不能简单地用 ``or``
    回退（因为字符串 ``"1.0000"`` 永远为 truthy）。此处通过解析为浮点数后判断：
    值 > 0 则使用，否则回退到 rate_org，再否则回退到 1.0。

    Args:
        my_rate_str: 用户自定义汇率，默认值 ``"1.0000"``，可能为空。
        rate_org_str: 中行官方汇率，可能为空。

    Returns:
        float: 有效的汇率值，始终 > 0。
    """
    # 优先尝试解析 my_rate
    try:
        v = float((my_rate_str or "").strip())
        if v > 0:
            return v
    except (ValueError, TypeError):
        pass

    # 回退到 rate_org
    try:
        v = float((rate_org_str or "").strip())
        if v > 0:
            return v
    except (ValueError, TypeError):
        pass

    # 最终兜底
    return 1.0


def build_campaign_profile_key(campaign_id: Any, profile_id: Any) -> str:
    """构建广告活动复合键字符串。

    数据库层已改为 campaign_id + profile_id 复合唯一，
    业务层的映射、聚合与匹配也必须使用相同的复合键，
    防止不同店铺出现相同 campaign_id 时发生数据混汇。

    Args:
        campaign_id (Any): 广告活动 ID。
        profile_id (Any): 店铺 Profile ID。

    Returns:
        str: 形如 ``"campaign_id::profile_id"`` 的稳定复合键。
    """
    return f"{str(campaign_id)}::{str(profile_id)}"


def build_campaign_profile_query(campaign_pairs: list[tuple[str, str]]) -> Q:
    """根据广告活动复合键列表构建 Q 查询条件。

    Args:
        campaign_pairs (list[tuple[str, str]]): 由 ``(campaign_id, profile_id)`` 组成的列表。

    Returns:
        Q: 可直接用于 Django ORM ``filter`` 的复合 OR 条件。
    """
    from django.db.models import Q as _Q
    pair_query = _Q()
    for campaign_id, profile_id in campaign_pairs:
        # 数据库 campaign_id / profile_id 均为 BigIntegerField 类型，
        # 而 campaign_pairs 传入的是 str，显式 int() 转换以确保 DB 索引命中
        try:
            pair_query |= _Q(campaign_id=int(campaign_id), profile_id=int(profile_id))
        except (ValueError, TypeError):
            continue
    return pair_query


def fmt_money(value: float | int, icon: str) -> str:
    """将数值格式化为带货币符号的字符串。

    Args:
        value (float | int): 待格式化的金额数值。
        icon (str): 货币符号，例如 ``$``、``€``、``£``。

    Returns:
        str: 格式化后的货币字符串，例如 ``"€123.45"``。
    """
    return f"{icon}{round(float(value), 2)}"
