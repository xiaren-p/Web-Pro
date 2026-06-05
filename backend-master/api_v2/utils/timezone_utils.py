"""站点时区工具（timezone_utils）。

根据 profile_id 或 timezone 字符串获取当前站点时间。
提供国家代码 → 时区的标准映射。
"""
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# 国家代码 → 时区映射（涵盖亚马逊主流站点）
_COUNTRY_TIMEZONE: dict[str, str] = {
    "US": "America/Los_Angeles",
    "CA": "America/Toronto",
    "MX": "America/Mexico_City",
    "BR": "America/Sao_Paulo",
    "GB": "Europe/London",
    "UK": "Europe/London",
    "DE": "Europe/Berlin",
    "FR": "Europe/Paris",
    "IT": "Europe/Rome",
    "ES": "Europe/Madrid",
    "NL": "Europe/Amsterdam",
    "SE": "Europe/Stockholm",
    "PL": "Europe/Warsaw",
    "BE": "Europe/Brussels",
    "TR": "Europe/Istanbul",
    "AE": "Asia/Dubai",
    "SA": "Asia/Riyadh",
    "IN": "Asia/Kolkata",
    "JP": "Asia/Tokyo",
    "AU": "Australia/Sydney",
    "SG": "Asia/Singapore",
    "CN": "Asia/Shanghai",
}


def country_to_timezone(country_code: str) -> str:
    """国家代码 → 时区。未知代码返回空字符串。

    Args:
        country_code: 国家代码，如 "DE"、"US"

    Returns:
        时区字符串，如 "Europe/Berlin"
    """
    if not country_code:
        return ""
    return _COUNTRY_TIMEZONE.get(str(country_code).upper(), "")


def get_local_time_by_profile(profile_id: int) -> datetime | None:
    """通过 profile_id 获取当前站点时间。

    Args:
        profile_id: 店铺 Profile ID

    Returns:
        当地 datetime（naive），失败返回 None
    """
    try:
        from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile

        cc = LxAdsProfile.objects.filter(profile_id=profile_id).values_list("country_code", flat=True).first()
        if not cc:
            return None
        tz_name = country_to_timezone(cc)
        if not tz_name:
            return None
        return datetime.now(ZoneInfo(tz_name)).replace(tzinfo=None)
    except (ZoneInfoNotFoundError, Exception):
        return None


def get_local_time_by_tz(tz_name: str) -> datetime | None:
    """根据时区名称获取当前站点时间。

    Args:
        tz_name: 时区名，如 "Europe/Madrid"

    Returns:
        当地 datetime（naive），失败返回 None
    """
    if not tz_name:
        return None
    try:
        return datetime.now(ZoneInfo(tz_name)).replace(tzinfo=None)
    except (ZoneInfoNotFoundError, Exception):
        return None


def get_local_time_str(tz_name: str) -> str | None:
    """获取当前站点时间字符串 "HH:MM"。

    Args:
        tz_name: 时区名

    Returns:
        "HH:MM" 字符串，失败返回 None
    """
    t = get_local_time_by_tz(tz_name)
    return t.strftime("%H:%M") if t else None
