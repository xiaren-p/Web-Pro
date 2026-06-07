"""分时策略共享工具（time_pricing_shared）。

提取 ad_time_pricing_service 和 time_pricing_service 共用的 segment 过滤与规则提取逻辑，
统一使用 UTC 标准时间，所有时段通过站点偏移量转 UTC 后比对。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

# UTC 标准时区（项目统一基准）
UTC_TZ = dt_timezone.utc

# 北京时间固定偏移（兼容旧接口，新代码请用 get_utc_now）
CN_TZ = dt_timezone(timedelta(hours=8))
CN_OFFSET_HOURS = 8

# 分时策略触发分布式锁 Key（Redis）；视图层入队前获取，入队后释放
TIME_PRICING_LOCK_KEY = "time_pricing_lock"


def get_utc_now() -> datetime:
    """获取当前 UTC 时间（aware datetime）。

    用于所有 segment 过滤与规则提取逻辑，统一时间基准。

    Returns:
        当前 UTC aware datetime
    """
    return datetime.now(UTC_TZ)


def get_cn_now() -> datetime:
    """获取当前北京时间（aware datetime，兼容旧接口）。

    Returns:
        当前北京时间 aware datetime
    """
    return datetime.now(CN_TZ)


def filter_segments_for_today(
    segments: list[dict],
    time_mode: str,
) -> list[dict]:
    """按当前 UTC 日期过滤 segments，仅返回今天适用的时段。

    三种模式过滤规则：
      - byDay：全部返回（每天适用）
      - byWeek：仅返回 dayOfWeek 等于今天周几的 seg（1=周一…7=周日）
      - calendar：返回全部（日历模式不分 segments）

    Args:
        segments: 策略 time_settings 中的 segments 列表
        time_mode: 策略 time_mode（byDay / byWeek / calendar）

    Returns:
        过滤后的 segments 列表，仅包含今天适用的时段
    """
    if not segments or not isinstance(segments, list):
        return []

    if time_mode == "byDay":
        return [seg for seg in segments if isinstance(seg, dict)]

    if time_mode == "byWeek":
        today_weekday = str(get_utc_now().isoweekday())  # "1" 周一 … "7" 周日
        return [
            seg for seg in segments
            if isinstance(seg, dict) and str(seg.get("dayOfWeek", "")) == today_weekday
        ]

    if time_mode == "calendar":
        return [seg for seg in segments if isinstance(seg, dict)]

    return []


def get_rules_for_segments(
    segments: list[dict],
    time_mode: str,
) -> list[dict]:
    """从今天适用的 segments 中提取全部规则（扁平合并）。

    先按当前日期过滤 segments，再遍历每个 seg 的 rules 列表拍平返回。
    调用方可根据需要进一步处理（如按时段分组或全部合并）。

    Args:
        segments: 策略 time_settings 中的 segments 列表
        time_mode: 策略 time_mode（byDay / byWeek / calendar）

    Returns:
        规则字典列表 [{"operateType": ..., "operateValue": ..., ...}]
    """
    filtered = filter_segments_for_today(segments, time_mode)
    rules: list[dict] = []
    for seg in filtered:
        if not isinstance(seg, dict):
            continue
        seg_rules = seg.get("rules", [])
        if isinstance(seg_rules, list):
            rules.extend(seg_rules)
    return rules
