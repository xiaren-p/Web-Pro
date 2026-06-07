"""广告分时策略命中服务（ad_time_pricing_service）。

职责：扫描新广告，匹配分时调价策略规则，写入命中记录。
"""
from __future__ import annotations

import json as _json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.db import connections
from django.db.models import Q
from django.utils import timezone as dj_timezone

from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile
from api_v1.models.lingxing.ads.basic.lx_sp_ad import LxSpAd
from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy, StrategyStatus
from api_v1.models.lingxing.sales.listing.lx_product_info import LxProductInfo
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, ManualRulesStatus, TimePricingHitStatus
from api_v2.services.ad_rules.strategy_matcher import match_strategy_against_product
from api_v2.services.ad_rules.time_pricing_shared import (
    UTC_TZ,
    filter_segments_for_today,
    get_utc_now,
)
from api_v2.utils.timezone_utils import country_to_timezone, get_fixed_utc_offset

logger = logging.getLogger(__name__)


# ============================================================
# 辅助函数
# ============================================================

def _parse_str_or_json_field(raw_val: Any) -> list[str]:
    """解析字段值（JSON 数组字符串或纯文本），返回扁平化值列表。"""
    if not raw_val:
        return []
    try:
        parsed = _json.loads(raw_val)
    except (_json.JSONDecodeError, TypeError):
        val = str(raw_val).strip()
        return [val] if val else []
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if item and str(item).strip()]
    val = str(raw_val).strip()
    return [val] if val else []


def _extract_principal_uids(principal_list: Any) -> list[int]:
    """从 principal_list JSON 字段提取所有 uid。"""
    if not principal_list:
        return []
    if isinstance(principal_list, str):
        try:
            principal_list = _json.loads(principal_list)
        except (_json.JSONDecodeError, TypeError):
            return []
    if not isinstance(principal_list, list):
        return []
    return list({
        item["uid"]
        for item in principal_list
        if isinstance(item, dict) and "uid" in item
    })


# ============================================================
# 时间计算
# ============================================================

def _calc_strategy_times(
    seg_start: str,
    seg_end: str,
    tz_name: str,
) -> tuple[datetime | None, datetime | None, datetime | None, datetime | None]:
    """根据分时时段（HH:MM）+ 站点时区偏移，计算四个时间。

    Args:
        seg_start: 时段开始时间（HH:MM 格式）
        seg_end: 时段结束时间（HH:MM 格式）
        tz_name: 站点时区名称（如 "America/Los_Angeles"）

    Returns:
        (time_start, time_end, time_start_cn, time_end_cn)：
        四个 aware datetime，站点时区与北京时区各一对
    """
    today = datetime.now().date()
    year = today.year

    sh, sm_val = map(int, seg_start.split(":"))
    eh, em = map(int, seg_end.split(":"))

    time_start_naive = datetime(year, today.month, today.day, sh, sm_val, 0)
    time_end_naive = datetime(year, today.month, today.day, eh, em, 0)
    if (eh, em) < (sh, sm_val):
        time_end_naive += timedelta(days=1)

    offset_hours = get_fixed_utc_offset(tz_name)
    site_tz = dt_timezone(timedelta(hours=offset_hours))
    cn_tz = dt_timezone(timedelta(hours=8))

    time_start = time_start_naive.replace(tzinfo=site_tz)
    time_end = time_end_naive.replace(tzinfo=site_tz)

    time_start_cn = time_start.astimezone(cn_tz)
    time_end_cn = time_end.astimezone(cn_tz)

    return time_start, time_end, time_start_cn, time_end_cn


def _resolve_segment_times(
    matched_strategy: LxTimePricingStrategy | None,
    tz: str,
) -> tuple[datetime | None, datetime | None, datetime | None, datetime | None]:
    """从策略的 time_settings 中解析时段边界时间。

    取所有时段的最小 start 和最大 end，合并为一个覆盖窗口。

    注意：该合并窗口仅用于 AdTimePricingHit 表的冗余存储（便于非策略上下文的快速查询），
    精确的时段判断（如 _in_time_range / _is_in_any_segment_now）应从策略表实时解析。

    Args:
        matched_strategy: 命中的分时策略实例，可为 None
        tz: 站点时区名称

    Returns:
        (time_start, time_end, time_start_cn, time_end_cn)，均为 aware datetime 或 None
    """
    if matched_strategy is None:
        return None, None, None, None

    segments = (matched_strategy.time_settings or {}).get("segments", [])
    filtered = filter_segments_for_today(segments, matched_strategy.time_mode)
    if not filtered:
        return None, None, None, None

    seg_times = [
        _calc_strategy_times(
            seg.get("startTime", "00:00"),
            seg.get("endTime", "00:00"),
            tz,
        )
        for seg in filtered
    ]
    valid_times = [(t[0], t[1], t[2], t[3]) for t in seg_times if t[0] is not None]
    if not valid_times:
        return None, None, None, None

    return (
        min(t[0] for t in valid_times),
        max(t[1] for t in valid_times),
        min(t[2] for t in valid_times),
        max(t[3] for t in valid_times),
    )


# ============================================================
# 策略匹配
# ============================================================

def match_strategy(
    profile_id: int,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
) -> dict[str, Any] | None:
    """匹配分时调价策略。

    Args:
        profile_id: 店铺 Profile ID
        product_assorts: 产品归类列表（已扁平去重）
        product_labels: 产品标签列表（已扁平去重）
        product_uids: 产品负责人 uid 列表（已扁平去重）

    Returns:
        {"strategy_id": int, "strategy_name": str} 或 None
    """
    strategies = list(
        LxTimePricingStrategy.objects
        .filter(status=StrategyStatus.ACTIVE)
        .order_by("weight", "-created_at")
    )
    return match_strategy_against_product(
        profile_id, product_assorts, product_labels, product_uids, strategies,
    )


# ============================================================
# Phase 1：数据预加载
# ============================================================

def _load_campaigns() -> tuple[
    list[tuple[int, int]],
    dict[tuple[int, int], dict[str, str]],
]:
    """加载所有 enabled 广告活动并获取时区信息。

    Returns:
        (campaign_pairs, campaign_meta)：
        campaign_pairs——有效的 (campaign_id, profile_id) 列表
        campaign_meta——{key: {"targeting_type": str, "timezone": str}}
    """
    campaigns_raw = list(
        LxSpCampaign.objects.filter(state="enabled")
        .values_list("campaign_id", "profile_id", "targeting_type")
    )
    campaign_pairs: list[tuple[int, int]] = []
    campaign_meta: dict[tuple[int, int], dict[str, str]] = {}
    for cid, pid, tt in campaigns_raw:
        campaign_pairs.append((cid, pid))
        campaign_meta[(cid, pid)] = {"targeting_type": tt or "auto", "timezone": ""}

    logger.info("[process_new_ads] campaign 总数=%d", len(campaign_pairs))

    # 关联店铺时区
    profile_ids = list({pid for _, pid in campaign_pairs})
    profile_timezones: dict[int, str] = {}
    for p in LxAdsProfile.objects.filter(
        profile_id__in=profile_ids, status=1,
    ).values("profile_id", "country_code"):
        profile_timezones[p["profile_id"]] = country_to_timezone(p["country_code"] or "")

    # 过滤无时区的店铺
    valid_pairs = {(cid, pid) for cid, pid in campaign_pairs if pid in profile_timezones}
    campaign_pairs = [(cid, pid) for cid, pid in campaign_pairs if (cid, pid) in valid_pairs]
    campaign_meta = {k: v for k, v in campaign_meta.items() if k in valid_pairs}
    for (cid, pid), meta in campaign_meta.items():
        meta["timezone"] = profile_timezones.get(pid, "")

    logger.info("[process_new_ads] 正常店铺 campaign=%d", len(campaign_pairs))
    return campaign_pairs, campaign_meta


def _load_ads_and_products(
    campaign_pairs: list[tuple[int, int]],
) -> tuple[
    dict[tuple[int, int], list[dict]],
    dict[str, dict[str, list[Any]]],
]:
    """批量加载广告与产品信息。

    Args:
        campaign_pairs: 有效的 campaign 键列表

    Returns:
        (campaign_to_ads, asin_to_fields)：
        campaign_to_ads——{key: [{"ad_id": int, "asin": str}]}
        asin_to_fields——{asin: {"assorts": [], "labels": [], "principal_uids": []}}
    """
    BATCH_Q_SIZE = 500
    all_ads_raw: list[LxSpAd] = []
    for i in range(0, len(campaign_pairs), BATCH_Q_SIZE):
        q_filter = Q()
        for cid, pid in campaign_pairs[i:i + BATCH_Q_SIZE]:
            q_filter |= Q(campaign_id=cid, profile_id=pid)
        all_ads_raw.extend(
            LxSpAd.objects.filter(q_filter)
            .only("campaign_id", "profile_id", "ad_id", "asin")
        )
    logger.info("[process_new_ads] 广告查询完成=%d", len(all_ads_raw))

    campaign_to_ads: dict[tuple[int, int], list[dict]] = defaultdict(list)
    all_asins: set[str] = set()
    for ad in all_ads_raw:
        key = (ad.campaign_id, ad.profile_id)
        campaign_to_ads[key].append({"ad_id": ad.ad_id, "asin": ad.asin or ""})
        if ad.asin:
            all_asins.add(ad.asin)
    logger.info("[process_new_ads] 有广告的 campaign=%d，唯一 ASIN=%d",
                len(campaign_to_ads), len(all_asins))

    asin_to_fields: dict[str, dict[str, list[Any]]] = {}
    if all_asins:
        products = LxProductInfo.objects.filter(asin__in=list(all_asins)).only(
            "asin", "assort", "label", "principal_list",
        )
        for p in products:
            asin_to_fields[p.asin] = {
                "assorts": _parse_str_or_json_field(p.assort),
                "labels": _parse_str_or_json_field(p.label),
                "principal_uids": _extract_principal_uids(p.principal_list),
            }
    logger.info("[process_new_ads] 产品信息命中 ASIN=%d", len(asin_to_fields))

    return campaign_to_ads, asin_to_fields


def _load_existing_hits(
    campaign_pairs: list[tuple[int, int]],
) -> dict[tuple[int, int], AdTimePricingHit]:
    """按 campaign_pairs 范围查询已有命中记录，避免全表扫描。

    Args:
        campaign_pairs: 有效的 campaign 键列表

    Returns:
        {(campaign_id, profile_id): AdTimePricingHit}
    """
    if not campaign_pairs:
        return {}

    # 构建 OR 条件精确查询（按 campaign_id, profile_id 做唯一过滤）
    campaign_ids = list({cid for cid, _ in campaign_pairs})
    profile_ids = list({pid for _, pid in campaign_pairs})

    existing_map: dict[tuple[int, int], AdTimePricingHit] = {}
    for h in AdTimePricingHit.objects.filter(
        campaign_id__in=campaign_ids,
        profile_id__in=profile_ids,
    ).iterator():
        existing_map[(h.campaign_id, h.profile_id)] = h

    logger.info("[process_new_ads] 已有记录=%d", len(existing_map))
    return existing_map


def _load_strategies() -> list[LxTimePricingStrategy]:
    """加载所有启用的分时策略，按优先级排序。

    Returns:
        已排序的策略实例列表
    """
    strategies = list(
        LxTimePricingStrategy.objects
        .filter(status=StrategyStatus.ACTIVE)
        .order_by("weight", "-created_at")
    )
    logger.info("[process_new_ads] 启用策略数=%d", len(strategies))
    return strategies


def _collect_campaign_product_fields(
    campaign_keys: list[tuple[int, int]],
    campaign_to_ads: dict[tuple[int, int], list[dict]],
    asin_to_fields: dict[str, dict[str, list[Any]]],
) -> dict[tuple[int, int], dict[str, Any]]:
    """按 campaign 聚合所有广告的字段信息（归类、标签、负责人）。

    对每个 campaign 遍历其所有广告，去重聚合 assorts / labels / uids。

    Args:
        campaign_keys: 需要处理的活动键列表
        campaign_to_ads: 活动→广告映射
        asin_to_fields: ASIN→字段映射

    Returns:
        {key: {"assorts": [], "labels": [], "uids": [], "has_sku": bool}}
    """
    result: dict[tuple[int, int], dict[str, Any]] = {}
    for cid, pid in campaign_keys:
        ads = campaign_to_ads.get((cid, pid), [])
        if not ads:
            continue

        assorts: list[str] = []
        labels: list[str] = []
        uids: list[int] = []
        seen_assorts: set[str] = set()
        seen_labels: set[str] = set()
        seen_uids: set[int] = set()
        has_sku = False

        for ad in ads:
            asin = ad.get("asin", "")
            if not asin:
                continue
            fields = asin_to_fields.get(asin)
            if not fields:
                continue
            has_sku = True
            for val in fields["assorts"]:
                if val not in seen_assorts:
                    seen_assorts.add(val)
                    assorts.append(val)
            for val in fields["labels"]:
                if val not in seen_labels:
                    seen_labels.add(val)
                    labels.append(val)
            for val in fields["principal_uids"]:
                if val not in seen_uids:
                    seen_uids.add(val)
                    uids.append(val)

        if has_sku:
            result[(cid, pid)] = {
                "assorts": assorts,
                "labels": labels,
                "uids": uids,
            }
    return result


# ============================================================
# Phase 2：命中匹配——新/已有 campaign 分别处理
# ============================================================

def _is_in_any_segment_now(hit: AdTimePricingHit, strategies: list[LxTimePricingStrategy]) -> bool:
    """判断当前 UTC 时间是否在命中记录的任一时段内。

    将 segment 中的站点当地时刻通过偏移量转为 UTC 后，与当前 UTC 时间比对。
    供 _process_existing_campaign 时段外跳过重匹配使用。

    Args:
        hit: 分时命中记录
        strategies: 预加载的策略列表

    Returns:
        True 表示当前在某个时段内
    """
    if not hit.hit_time_pricing_rules:
        return False

    strategy = next(
        (s for s in strategies if str(s.id) == str(hit.hit_time_pricing_rules)), None,
    )
    if strategy is None:
        return False

    now_utc = get_utc_now()
    site_offset = get_fixed_utc_offset(hit.timezone)

    time_settings = strategy.time_settings or {}
    segments = (time_settings.get("segments", []) if isinstance(time_settings, dict) else [])
    filtered = filter_segments_for_today(segments, strategy.time_mode)
    if not filtered:
        return False

    for seg in filtered:
        start_str = (seg or {}).get("startTime", "00:00")
        end_str = (seg or {}).get("endTime", "00:00")
        try:
            today = now_utc.date()
            y = today.year

            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))

            seg_start_naive = datetime(y, today.month, today.day, sh, sm, 0)
            seg_end_naive = datetime(y, today.month, today.day, eh, em, 0)
            if (eh, em) < (sh, sm):
                seg_end_naive = seg_start_naive + timedelta(days=1)

            # segment 时间是站点当地时区 → 转 UTC
            site_tz = dt_timezone(timedelta(hours=site_offset))
            seg_start_utc = seg_start_naive.replace(tzinfo=site_tz).astimezone(UTC_TZ)
            seg_end_utc = seg_end_naive.replace(tzinfo=site_tz).astimezone(UTC_TZ)

            if seg_start_utc <= now_utc <= seg_end_utc:
                return True
        except (ValueError, TypeError):
            continue

    return False

def _process_new_campaign(
    cid: int,
    pid: int,
    campaign_fields: dict[str, Any],
    campaign_meta: dict[tuple[int, int], dict[str, str]],
    strategies: list[LxTimePricingStrategy],
    now: datetime,
) -> AdTimePricingHit | None:
    """为新 campaign 执行策略匹配并构建命中记录。

    执行策略匹配 → 命中时计算时间边界 → 返回新 AdTimePricingHit 实例。

    Args:
        cid: 广告活动 ID
        pid: 店铺 Profile ID
        campaign_fields: 预聚合的字段信息（assorts, labels, uids）
        campaign_meta: 活动元信息（targeting_type, timezone）
        strategies: 预加载的策略列表
        now: 当前时间

    Returns:
        新构建的 AdTimePricingHit 实例，未命中时返回 None
    """
    result = match_strategy_against_product(
        pid,
        campaign_fields["assorts"],
        campaign_fields["labels"],
        campaign_fields["uids"],
        strategies,
    )
    if not result:
        return None

    tz = campaign_meta.get((cid, pid), {}).get("timezone", "")
    targeting_type = campaign_meta.get((cid, pid), {}).get("targeting_type", "auto")

    matched_strategy = next(
        (s for s in strategies if s.id == result["strategy_id"]), None,
    )
    ts, te, ts_cn, te_cn = _resolve_segment_times(matched_strategy, tz)

    return AdTimePricingHit(
        campaign_id=cid,
        profile_id=pid,
        targeting_type=targeting_type,
        timezone=tz,
        hit_time_pricing_rules=str(result["strategy_id"]),
        is_time_pricing=TimePricingHitStatus.NO,
        time_start=ts,
        time_end=te,
        time_start_cn=ts_cn,
        time_end_cn=te_cn,
        awaiting_start=TimePricingHitStatus.YES,
        is_manual_rules=ManualRulesStatus.NO,
        manual_rule_id="",
        rule_updated_today=True,
        created_at=now,
        updated_at=now,
    )


def _process_existing_campaign(
    cid: int,
    pid: int,
    existing: AdTimePricingHit,
    campaign_fields: dict[str, Any],
    campaign_meta: dict[tuple[int, int], dict[str, str]],
    strategies: list[LxTimePricingStrategy],
    now: datetime,
) -> AdTimePricingHit | None:
    """为已有命中记录的活动执行规则更新。

    按优先级判断：
      1. 已在分时生效中 → 跳过
      2. 今日已更新且有规则 → 跳过
      3. 用户手动规则 → 按手动策略更新
      4. 常规策略匹配 → 更新命中规则与时间
      5. 已有规则且不在任一时段内 → 跳过（防翻转 trivial reset）

    Args:
        cid: 广告活动 ID
        pid: 店铺 Profile ID
        existing: 已有命中记录
        campaign_fields: 预聚合的字段信息
        campaign_meta: 活动元信息
        strategies: 预加载的策略列表
        now: 当前时间

    Returns:
        需要更新的 AdTimePricingHit 实例，无需更新时返回 None
    """
    # 已在分时生效中，跳过
    if existing.is_time_pricing == TimePricingHitStatus.YES:
        return None

    # 今日已更新且有规则，跳过
    # 例外：命中的策略已被暂停/删除，必须放行重匹配
    if existing.rule_updated_today and existing.hit_time_pricing_rules and existing.hit_time_pricing_rules in {str(s.id) for s in strategies}:
        return None

    tz = campaign_meta.get((cid, pid), {}).get("timezone", "")

    # 用户手动规则路径
    if existing.is_manual_rules == ManualRulesStatus.YES and existing.manual_rule_id:
        updated = _apply_manual_rule(existing, strategies, tz, now)
        if updated is not None:
            return updated
        # 用户策略不存在（已删除）→ 降级到常规策略匹配

    # 已有规则且不在任一时段内：跳过重匹配，避免每小时无意义的
    # process_new_ads() 重匹配 → execute() 兜底 reset 反复翻转
    # 例外：rule_updated_today=False 时分时回调刚结束或规则已变更，必须放行重匹配
    if existing.hit_time_pricing_rules and existing.rule_updated_today:
        if not _is_in_any_segment_now(existing, strategies):
            return None

    # 常规策略匹配路径
    result = match_strategy_against_product(
        pid,
        campaign_fields["assorts"],
        campaign_fields["labels"],
        campaign_fields["uids"],
        strategies,
    )
    existing.hit_time_pricing_rules = str(result["strategy_id"]) if result else ""
    existing.rule_updated_today = True
    existing.awaiting_start = TimePricingHitStatus.YES
    existing.is_time_pricing = TimePricingHitStatus.NO

    if result:
        matched_strategy = next(
            (s for s in strategies if s.id == result["strategy_id"]), None,
        )
        ts, te, ts_cn, te_cn = _resolve_segment_times(matched_strategy, tz)
        existing.time_start = ts
        existing.time_end = te
        existing.time_start_cn = ts_cn
        existing.time_end_cn = te_cn

    existing.updated_at = now
    return existing


def _apply_manual_rule(
    existing: AdTimePricingHit,
    strategies: list[LxTimePricingStrategy],
    tz: str,
    now: datetime,
) -> AdTimePricingHit | None:
    """应用用户手动指定的策略规则。

    在策略列表中查找用户指定的 manual_rule_id，
    若策略存在则更新命中规则与时间边界。

    Args:
        existing: 已有命中记录
        strategies: 预加载的策略列表
        tz: 站点时区名称
        now: 当前时间

    Returns:
        更新后的 AdTimePricingHit，用户策略不存在时返回 None
    """
    user_strategy = next(
        (s for s in strategies if str(s.id) == str(existing.manual_rule_id)), None,
    )
    if user_strategy is None:
        return None

    existing.hit_time_pricing_rules = existing.manual_rule_id
    existing.rule_updated_today = True
    existing.awaiting_start = TimePricingHitStatus.YES
    existing.is_time_pricing = TimePricingHitStatus.NO

    ts, te, ts_cn, te_cn = _resolve_segment_times(user_strategy, tz)
    existing.time_start = ts
    existing.time_end = te
    existing.time_start_cn = ts_cn
    existing.time_end_cn = te_cn

    existing.updated_at = now
    return existing


# ============================================================
# Phase 3：多线程调度 + 批量写入
# ============================================================

def _process_chunk(
    campaign_keys: list[tuple[int, int]],
    campaign_to_ads: dict[tuple[int, int], list[dict]],
    asin_to_fields: dict[str, dict[str, list[Any]]],
    existing_map: dict[tuple[int, int], AdTimePricingHit],
    strategies: list[LxTimePricingStrategy],
    campaign_meta: dict[tuple[int, int], dict[str, str]],
) -> dict[str, Any]:
    """线程入口：处理一批 campaign，收集新建与更新记录。

    先聚合字段→再分流新/已有 campaign 分别处理→收集结果。

    Args:
        campaign_keys: 本线程负责的活动键列表
        campaign_to_ads: 活动→广告映射（共享读）
        asin_to_fields: ASIN→产品字段映射（共享读）
        existing_map: 已有命中记录映射（共享读）
        strategies: 预加载的策略列表（共享读）
        campaign_meta: 活动元信息（共享读）

    Returns:
        {"hits": [], "updates": [], "processed": int, "hit_count": int}
    """
    connections.close_all()

    # 聚合字段——仅本线程可见
    fields_map = _collect_campaign_product_fields(
        campaign_keys, campaign_to_ads, asin_to_fields,
    )

    new_records: list[AdTimePricingHit] = []
    update_records: list[AdTimePricingHit] = []
    processed = 0
    hit_count = 0
    now = dj_timezone.now()

    for key in campaign_keys:
        if key not in fields_map:
            continue

        cid, pid = key
        existing = existing_map.get(key)
        fields = fields_map[key]

        if existing is None:
            hit = _process_new_campaign(
                cid, pid, fields, campaign_meta, strategies, now,
            )
            if hit is None:
                continue
            new_records.append(hit)
            processed += 1
            hit_count += 1
        else:
            updated = _process_existing_campaign(
                cid, pid, existing, fields, campaign_meta, strategies, now,
            )
            if updated is None:
                continue
            update_records.append(updated)
            processed += 1
            if updated.hit_time_pricing_rules:
                hit_count += 1

    return {
        "hits": new_records,
        "updates": update_records,
        "processed": processed,
        "hit_count": hit_count,
    }


# ============================================================
# 主流程
# ============================================================

def process_new_ads() -> dict[str, Any]:
    """批量预加载 + 多线程并行命中，写入 AdTimePricingHit 记录。

    Returns:
        {"total_campaigns", "new_ads_processed", "hits", "written", "errors"}
    """
    MAX_WORKERS = 4

    # Phase 1：批量预加载
    campaign_pairs, campaign_meta = _load_campaigns()
    total_campaigns = len(campaign_pairs)
    if not campaign_pairs:
        return {"total_campaigns": 0, "new_ads_processed": 0, "hits": 0, "written": 0, "errors": []}

    campaign_to_ads, asin_to_fields = _load_ads_and_products(campaign_pairs)
    existing_map = _load_existing_hits(campaign_pairs)
    strategies = _load_strategies()

    # 筛选有广告的 campaign
    campaign_list = [k for k in campaign_pairs if k in campaign_to_ads]
    if not campaign_list:
        return {"total_campaigns": total_campaigns, "new_ads_processed": 0,
                "hits": 0, "written": 0, "errors": []}

    # Phase 2：多线程并行匹配
    chunk_size = max(1, len(campaign_list) // MAX_WORKERS)
    chunks = [campaign_list[i:i + chunk_size]
              for i in range(0, len(campaign_list), chunk_size)][:MAX_WORKERS]

    errors: list[str] = []
    all_hits: list[AdTimePricingHit] = []
    all_updates: list[AdTimePricingHit] = []
    total_processed = 0
    total_hits = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(
                _process_chunk, chunk, campaign_to_ads, asin_to_fields,
                existing_map, strategies, campaign_meta,
            )
            for chunk in chunks
        ]
        for future in as_completed(futures):
            result = future.result()
            all_hits.extend(result["hits"])
            all_updates.extend(result["updates"])
            total_processed += result["processed"]
            total_hits += result["hit_count"]

    # Phase 3：批量写入
    if all_hits:
        AdTimePricingHit.objects.bulk_create(all_hits, batch_size=500)
    if all_updates:
        AdTimePricingHit.objects.bulk_update(
            all_updates,
            [
                "hit_time_pricing_rules",
                "rule_updated_today",
                "time_start",
                "time_end",
                "time_start_cn",
                "time_end_cn",
                "awaiting_start",
                "is_time_pricing",
                "updated_at",
            ],
            batch_size=500,
        )

    logger.info(
        "[process_new_ads] 完成 campaigns=%d new=%d hits=%d updates=%d",
        total_campaigns, len(all_hits), total_hits, len(all_updates),
    )
    return {
        "total_campaigns": total_campaigns,
        "new_ads_processed": total_processed,
        "hits": total_hits,
        "written": len(all_hits) + len(all_updates),
        "errors": errors,
    }
