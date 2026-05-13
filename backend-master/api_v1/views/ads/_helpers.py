"""ads 板块视图共用辅助：国家映射、复合键构造、货币符号查询。

仅供 ``api_v1.views.ads`` 包内 ViewSet 复用。跨包的业务计算请放入
``api_v1.services``。
"""
from __future__ import annotations

from typing import Any

from django.db.models import Q

from api_v1.models import CurrencyIcon, LxCurrencyRates, LxShopProfile

# 国家代码到中文名称的全局映射
COUNTRY_MAP: dict[str, str] = {
    "FR": "法国", "IT": "意大利", "BE": "比利时", "UK": "英国",
    "PL": "波兰", "NL": "荷兰", "SE": "瑞典", "ES": "西班牙",
    "DE": "德国", "US": "美国", "CA": "加拿大", "JP": "日本",
    "MX": "墨西哥", "AU": "澳大利亚", "SG": "新加坡", "TR": "土耳其",
    "IN": "印度", "AE": "阿联酋", "SA": "沙特", "BR": "巴西",
}

# 货币查询失败时的安全 fallback
FALLBACK_CCY: dict[str, Any] = {"icon": "$", "code": "USD", "rate": 1.0}


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
    pair_query = Q()
    for campaign_id, profile_id in campaign_pairs:
        pair_query |= Q(campaign_id=campaign_id, profile_id=profile_id)
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


def resolve_currency_icon(profile_id: str) -> str:
    """根据 ``profile_id`` 查询对应店铺的货币符号。

    查询链路：``lx_shop_profiles.country`` → ``currency_icon.code`` → ``lx_currency_rates.icon``。
    三张表均有唯一索引，三次点查（Primary Key Lookup），总体 I/O 极低。

    Args:
        profile_id (str): 店铺 Profile ID。

    Returns:
        str: 货币符号；查询失败则返回 ``"$"``。
    """
    shop = LxShopProfile.objects.filter(profile_id=profile_id).first()
    if not shop or not shop.country:
        return FALLBACK_CCY["icon"]

    ci = CurrencyIcon.objects.filter(country=shop.country).first()
    if not ci or not ci.code:
        return FALLBACK_CCY["icon"]

    cr = LxCurrencyRates.objects.filter(code=ci.code).first()
    if not cr:
        return FALLBACK_CCY["icon"]

    return cr.icon or FALLBACK_CCY["icon"]
