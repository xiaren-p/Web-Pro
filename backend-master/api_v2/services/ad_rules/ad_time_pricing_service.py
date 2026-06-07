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
    filter_segments_for_today,
)
from api_v2.utils.timezone_utils import country_to_timezone, get_fixed_utc_offset

logger = logging.getLogger(__name__)

CN_TZ = dt_timezone(timedelta(hours=8))


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
    """根据分时时段（HH:MM）+ 站点时区偏移，计算四个时间。"""
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


# ============================================================
# 策略匹配
# ============================================================

def match_strategy(
    profile_id: int,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
) -> dict[str, Any] | None:
    """匹配分时调价策略。"""
    strategies = list(
        LxTimePricingStrategy.objects
        .filter(status=StrategyStatus.ACTIVE)
        .order_by("weight", "-created_at")
    )
    return match_strategy_against_product(
        profile_id, product_assorts, product_labels, product_uids, strategies,
    )


# ============================================================
# 主流程
# ============================================================

def process_new_ads() -> dict[str, Any]:
    """批量预加载 + 多线程并行命中，写入 AdTimePricingHit 记录。"""
    MAX_WORKERS = 4
    BATCH_Q_SIZE = 500

    # Phase 1：批量预加载
    campaigns_raw = list(
        LxSpCampaign.objects.filter(state="enabled")
        .values_list("campaign_id", "profile_id", "targeting_type")
    )
    campaign_pairs: list[tuple[int, int]] = []
    campaign_meta: dict[tuple[int, int], dict[str, str]] = {}
    for cid, pid, tt in campaigns_raw:
        campaign_pairs.append((cid, pid))
        campaign_meta[(cid, pid)] = {"targeting_type": tt or "auto", "timezone": ""}
    total_campaigns = len(campaign_pairs)
    logger.info("[process_new_ads] campaign 总数=%d", total_campaigns)

    profile_ids = list({pid for _, pid in campaign_pairs})
    profile_timezones: dict[int, str] = {}
    for p in LxAdsProfile.objects.filter(
        profile_id__in=profile_ids, status=1,
    ).values("profile_id", "country_code"):
        profile_timezones[p["profile_id"]] = country_to_timezone(p["country_code"] or "")
    valid_pairs = {(cid, pid) for cid, pid in campaign_pairs if pid in profile_timezones}
    campaign_pairs = [(cid, pid) for cid, pid in campaign_pairs if (cid, pid) in valid_pairs]
    campaign_meta = {k: v for k, v in campaign_meta.items() if k in valid_pairs}
    for (cid, pid), meta in campaign_meta.items():
        meta["timezone"] = profile_timezones.get(pid, "")
    total_campaigns = len(campaign_pairs)
    logger.info("[process_new_ads] 正常店铺 campaign=%d", total_campaigns)
    if not campaign_pairs:
        return {"total_campaigns": 0, "new_ads_processed": 0, "hits": 0, "written": 0, "errors": []}

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

    existing_map: dict[tuple[int, int], AdTimePricingHit] = {
        (h.campaign_id, h.profile_id): h
        for h in AdTimePricingHit.objects.all()
    }
    logger.info("[process_new_ads] 已有记录=%d", len(existing_map))

    strategies: list[LxTimePricingStrategy] = list(
        LxTimePricingStrategy.objects
        .filter(status=StrategyStatus.ACTIVE)
        .order_by("weight", "-created_at")
    )
    logger.info("[process_new_ads] 启用策略数=%d", len(strategies))

    # Phase 2：多线程并行匹配
    campaign_list = [k for k in campaign_pairs if k in campaign_to_ads]
    if not campaign_list:
        return {"total_campaigns": total_campaigns, "new_ads_processed": 0,
                "hits": 0, "written": 0, "errors": []}

    chunk_size = max(1, len(campaign_list) // MAX_WORKERS)
    chunks = [campaign_list[i:i + chunk_size]
              for i in range(0, len(campaign_list), chunk_size)][:MAX_WORKERS]
    now = dj_timezone.now()

    def _worker(campaign_keys: list[tuple[int, int]]) -> dict[str, Any]:
        connections.close_all()

        new_records: list[AdTimePricingHit] = []
        update_records: list[AdTimePricingHit] = []
        processed = 0
        hit_count = 0

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

            if not has_sku:
                continue

            tz = campaign_meta.get((cid, pid), {}).get("timezone", "")
            targeting_type = campaign_meta.get((cid, pid), {}).get("targeting_type", "auto")
            existing = existing_map.get((cid, pid))

            if existing is None:
                result = match_strategy_against_product(pid, assorts, labels, uids, strategies)
                if not result:
                    continue

                matched_strategy = next(
                    (s for s in strategies if s.id == result["strategy_id"]), None,
                )
                ts = te = ts_cn = te_cn = None
                if matched_strategy:
                    segments = (matched_strategy.time_settings or {}).get("segments", [])
                    filtered = filter_segments_for_today(segments, matched_strategy.time_mode)
                    if filtered:
                        seg_times = [
                            _calc_strategy_times(
                                seg.get("startTime", "00:00"),
                                seg.get("endTime", "00:00"),
                                tz,
                            )
                            for seg in filtered
                        ]
                        valid_times = [(t[0], t[1], t[2], t[3]) for t in seg_times if t[0] is not None]
                        if valid_times:
                            ts = min(t[0] for t in valid_times)
                            te = max(t[1] for t in valid_times)
                            ts_cn = min(t[2] for t in valid_times)
                            te_cn = max(t[3] for t in valid_times)

                new_records.append(AdTimePricingHit(
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
                ))
                processed += 1
                hit_count += 1
                continue

            if existing.is_time_pricing == TimePricingHitStatus.YES:
                continue

            if existing.rule_updated_today and existing.hit_time_pricing_rules:
                continue

            if existing.is_manual_rules == ManualRulesStatus.YES and existing.manual_rule_id:
                user_strategy = next(
                    (s for s in strategies if str(s.id) == str(existing.manual_rule_id)), None,
                )
                if user_strategy:
                    existing.hit_time_pricing_rules = existing.manual_rule_id
                    existing.rule_updated_today = True
                    existing.awaiting_start = TimePricingHitStatus.YES
                    existing.is_time_pricing = TimePricingHitStatus.NO
                    segments = (user_strategy.time_settings or {}).get("segments", [])
                    filtered = filter_segments_for_today(segments, user_strategy.time_mode)
                    if filtered:
                        seg_times = [
                            _calc_strategy_times(
                                seg.get("startTime", "00:00"),
                                seg.get("endTime", "00:00"),
                                tz,
                            )
                            for seg in filtered
                        ]
                        valid_times = [(t[0], t[1], t[2], t[3]) for t in seg_times if t[0] is not None]
                        if valid_times:
                            existing.time_start = min(t[0] for t in valid_times)
                            existing.time_end = max(t[1] for t in valid_times)
                            existing.time_start_cn = min(t[2] for t in valid_times)
                            existing.time_end_cn = max(t[3] for t in valid_times)
                    existing.updated_at = now
                    update_records.append(existing)
                    processed += 1
                    hit_count += 1
                    continue

            result = match_strategy_against_product(pid, assorts, labels, uids, strategies)
            existing.hit_time_pricing_rules = str(result["strategy_id"]) if result else ""
            existing.rule_updated_today = True
            existing.awaiting_start = TimePricingHitStatus.YES
            existing.is_time_pricing = TimePricingHitStatus.NO
            if result:
                matched_strategy = next(
                    (s for s in strategies if s.id == result["strategy_id"]), None,
                )
                if matched_strategy:
                    segments = (matched_strategy.time_settings or {}).get("segments", [])
                    filtered = filter_segments_for_today(segments, matched_strategy.time_mode)
                    if filtered:
                        seg_times = [
                            _calc_strategy_times(
                                seg.get("startTime", "00:00"),
                                seg.get("endTime", "00:00"),
                                tz,
                            )
                            for seg in filtered
                        ]
                        valid_times = [(t[0], t[1], t[2], t[3]) for t in seg_times if t[0] is not None]
                        if valid_times:
                            existing.time_start = min(t[0] for t in valid_times)
                            existing.time_end = max(t[1] for t in valid_times)
                            existing.time_start_cn = min(t[2] for t in valid_times)
                            existing.time_end_cn = max(t[3] for t in valid_times)
            existing.updated_at = now
            update_records.append(existing)
            processed += 1
            if result:
                hit_count += 1

        return {
            "hits": new_records,
            "updates": update_records,
            "processed": processed,
            "hit_count": hit_count,
        }

    # Phase 3：写入
    errors: list[str] = []
    all_hits: list[AdTimePricingHit] = []
    all_updates: list[AdTimePricingHit] = []
    total_processed = 0
    total_hits = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_worker, chunk) for chunk in chunks]
        for future in as_completed(futures):
            result = future.result()
            all_hits.extend(result["hits"])
            all_updates.extend(result["updates"])
            total_processed += result["processed"]
            total_hits += result["hit_count"]

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
