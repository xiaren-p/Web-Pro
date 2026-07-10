"""SP 广告货币符号查询选择器。

从 ``LxAdsProfile.currency_code`` → ``LxExchangeRate.icon`` 链路查询货币符号。
6 个 ViewSet 共用此选择器，避免重复实现。
"""
import logging

from apps.ads.models.lx_ads_profile import LxAdsProfile
from apps.lingxing_basic.models.lx_exchange_rate import LxExchangeRate

logger = logging.getLogger(__name__)


def resolve_currency_icon(profile_id: int) -> str:
    """根据 profile_id 查询货币符号（一步查表）。

    查询链路：LxAdsProfile.currency_code → LxExchangeRate.code → icon。
    取最新月份的汇率记录。

    Args:
        profile_id (int): 店铺 Profile ID。

    Returns:
        str: 货币符号，查询失败返回 "?"。
    """
    profile = LxAdsProfile.objects.filter(profile_id=profile_id).first()
    if not profile or not profile.currency_code:
        return "?"
    rate = LxExchangeRate.objects.filter(
        code=profile.currency_code,
    ).order_by("-date").first()
    return rate.icon if rate and rate.icon else "?"
