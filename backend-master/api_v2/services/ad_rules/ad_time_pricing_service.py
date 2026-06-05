"""广告分时策略命中服务（ad_time_pricing_service）。

职责：扫描新广告，匹配分时调价策略规则，写入命中记录。
"""
from __future__ import annotations

import json as _json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
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
from api_v2.utils.timezone_utils import country_to_timezone, get_fixed_utc_offset

logger = logging.getLogger(__name__)


# ============================================================
# 辅助函数
# ============================================================

def _parse_str_or_json_field(raw_val: Any) -> list[str]:
    """解析字段值（JSON 数组字符串或纯文本），返回扁平化值列表。

    Args:
        raw_val: 可能是 JSON 字符串、纯文本字符串或 None/空

    Returns:
        解析后的字符串列表（已去空去重）
    """
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
    """从 principal_list JSON 字段提取所有 uid。

    Args:
        principal_list: JSON 字符串或已解析的 list[dict]

    Returns:
        uid 整数列表（去重）
    """
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
    strategy: LxTimePricingStrategy,
    seg_start: str,
    seg_end: str,
    tz_name: str,
) -> tuple[datetime | None, datetime | None, datetime | None, datetime | None]:
    """根据分时时段（HH:MM）+ 站点时区偏移，计算四个时间。

    time_start / time_end：规则原始时间（站点 local time），带站点固定偏移 tzinfo。
    time_start_cn / time_end_cn：北京时间（固定偏移 +8），带北京 tzinfo。
    两者指向同一 UTC 时刻，Django 据此正确存储。

    例如规则 06:00～01:00，站点 Europe/Rome（固定偏移 +1）：
      time_start     = 2026-06-05 06:00+01:00 → DB UTC 05:00
      time_end       = 2026-06-06 01:00+01:00 → DB UTC 00:00
      time_start_cn  = 2026-06-05 13:00+08:00 → DB UTC 05:00（同一时刻）
      time_end_cn    = 2026-06-06 08:00+08:00 → DB UTC 00:00（同一时刻）
    """
    from datetime import timezone as dt_timezone

    sm = strategy.start_month
    sd = strategy.start_day

    today = datetime.now().date()
    year = today.year

    # start_month/start_day 为 null 时不限时间，使用当天日期
    if sm is None or sd is None:
        sm = today.month
        sd = today.day

    sh, sm_val = map(int, seg_start.split(":"))
    eh, em = map(int, seg_end.split(":"))

    # ── 站点本地时间 naive 结构 ──
    time_start_naive = datetime(year, today.month, today.day, sh, sm_val, 0)
    time_end_naive = datetime(year, today.month, today.day, eh, em, 0)
    if (eh, em) < (sh, sm_val):
        time_end_naive += timedelta(days=1)  # 跨天

    # ── 固定偏移（项目铁律，不分夏冬令时）──
    offset_hours = get_fixed_utc_offset(tz_name)
    site_tz = dt_timezone(timedelta(hours=offset_hours))
    cn_tz = dt_timezone(timedelta(hours=8))

    # time_start / time_end：站点当地时间 + 站点固定偏移
    time_start = time_start_naive.replace(tzinfo=site_tz)
    time_end = time_end_naive.replace(tzinfo=site_tz)

    # time_start_cn / time_end_cn：同一时刻，转为北京时间固定偏移
    time_start_cn = time_start.astimezone(cn_tz)
    time_end_cn = time_end.astimezone(cn_tz)

    return time_start, time_end, time_start_cn, time_end_cn


def _filter_segments_for_today(
    segments: list[dict],
    time_mode: str,
) -> list[dict]:
    """按当前日期过滤 segments，仅返回今天适用的时段。

    三种模式过滤规则：
      - byDay：全部返回（每天适用）
      - byWeek：仅返回 dayOfWeek 等于今天周几的 seg（1=周一…7=周日）
      - calendar：返回全部（日历模式不分 segments）

    Args:
        segments: 策略 time_settings 中的 segments 列表
        time_mode: 策略 time_mode（byDay / byWeek / calendar）

    Returns:
        过滤后的 segments 列表
    """
    if not segments or not isinstance(segments, list):
        return []

    if time_mode == "byDay":
        return [seg for seg in segments if isinstance(seg, dict)]

    if time_mode == "byWeek":
        today_weekday = str(datetime.now().isoweekday())  # "1" 周一 … "7" 周日
        return [
            seg for seg in segments
            if isinstance(seg, dict) and str(seg.get("dayOfWeek", "")) == today_weekday
        ]

    if time_mode == "calendar":
        return [seg for seg in segments if isinstance(seg, dict)]

    return []


# ============================================================
# 策略匹配（便捷封装）
# ============================================================

def match_strategy(
    profile_id: int,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
) -> dict[str, Any] | None:
    """匹配分时调价策略：查库加载开启策略，委托 strategy_matcher 匹配。

    Args:
        profile_id: 店铺 Profile ID
        product_assorts: 产品归类列表
        product_labels: 产品标签列表
        product_uids: 产品负责人 uid 列表

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
# 主流程：扫描新广告并命中策略
# ============================================================

def process_new_ads() -> dict[str, Any]:
    """批量预加载 + 多线程并行命中，写入 AdTimePricingHit 记录。

    三步走：
    - Phase 1：批量预加载 campaigns / ads / products / 已有记录 / 策略
    - Phase 2：多线程并行，纯内存匹配
    - Phase 3：批量写入新记录 + 批量更新已有记录

    匹配规则：
    - 新 campaign → 必须有 ASIN 能匹配到产品信息 → 必须命中策略 → 创建记录
    - 已有记录 → 正在分时（is_time_pricing=YES）→ 跳过
    - 已有记录 → 当日已更新（rule_updated_today=True）→ 跳过
    - 已有记录 → 未分时 + 未更新 → 重新命中并 UPDATE

    Returns:
        {
            "total_campaigns": int,
            "new_ads_processed": int,
            "hits": int,
            "written": int,
            "errors": list[str],
        }
    """
    MAX_WORKERS = 4
    BATCH_Q_SIZE = 500

    # ── Phase 1：批量预加载 ──────────────────────────────────────────────

    # 1a. 获取所有 enabled 状态的 campaign
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

    # 1b. 时区映射：profile_id → 国家 → 时区 → campaign_meta
    profile_ids = list({pid for _, pid in campaign_pairs})
    profile_timezones: dict[int, str] = {}
    for p in LxAdsProfile.objects.filter(
        profile_id__in=profile_ids, status=1,
    ).values("profile_id", "country_code"):
        profile_timezones[p["profile_id"]] = country_to_timezone(p["country_code"] or "")
    # 只保留店铺状态正常的 campaign
    valid_pairs = {(cid, pid) for cid, pid in campaign_pairs if pid in profile_timezones}
    campaign_pairs = [(cid, pid) for cid, pid in campaign_pairs if (cid, pid) in valid_pairs]
    campaign_meta = {k: v for k, v in campaign_meta.items() if k in valid_pairs}
    for (cid, pid), meta in campaign_meta.items():
        meta["timezone"] = profile_timezones.get(pid, "")
    total_campaigns = len(campaign_pairs)
    logger.info("[process_new_ads] 正常店铺 campaign=%d", total_campaigns)
    if not campaign_pairs:
        return {"total_campaigns": 0, "new_ads_processed": 0, "hits": 0, "written": 0, "errors": []}

    # 1c. 批量查广告
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

    # 1d. 构建 campaign → ads 映射 + 收集唯一 ASIN
    campaign_to_ads: dict[tuple[int, int], list[dict]] = defaultdict(list)
    all_asins: set[str] = set()
    for ad in all_ads_raw:
        key = (ad.campaign_id, ad.profile_id)
        campaign_to_ads[key].append({"ad_id": ad.ad_id, "asin": ad.asin or ""})
        if ad.asin:
            all_asins.add(ad.asin)
    logger.info("[process_new_ads] 有广告的 campaign=%d，唯一 ASIN=%d",
                len(campaign_to_ads), len(all_asins))

    # 1e. 批量查产品信息，构建 asin → 字段映射
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

    # 1f. 预查已有记录，构建 (cid, pid) → AdTimePricingHit 映射
    existing_map: dict[tuple[int, int], AdTimePricingHit] = {
        (h.campaign_id, h.profile_id): h
        for h in AdTimePricingHit.objects.all()
    }
    logger.info("[process_new_ads] 已有记录=%d", len(existing_map))

    # 1g. 预加载所有开启的策略（按 weight 升序）
    strategies: list[LxTimePricingStrategy] = list(
        LxTimePricingStrategy.objects
        .filter(status=StrategyStatus.ACTIVE)
        .order_by("weight", "-created_at")
    )
    logger.info("[process_new_ads] 启用策略数=%d", len(strategies))

    # ── Phase 2：多线程并行匹配 ──────────────────────────────────────────

    campaign_list = [k for k in campaign_pairs if k in campaign_to_ads]
    if not campaign_list:
        return {"total_campaigns": total_campaigns, "new_ads_processed": 0,
                "hits": 0, "written": 0, "errors": []}

    chunk_size = max(1, len(campaign_list) // MAX_WORKERS)
    chunks = [campaign_list[i:i + chunk_size]
              for i in range(0, len(campaign_list), chunk_size)][:MAX_WORKERS]
    now = dj_timezone.now()

    def _worker(campaign_keys: list[tuple[int, int]]) -> dict[str, Any]:
        """线程入口：处理分配给自己的 campaign 分片。

        本线程内不访问数据库，所有数据由主线程预加载到内存中。
        """
        connections.close_all()

        new_records: list[AdTimePricingHit] = []      # 批量创建
        update_records: list[AdTimePricingHit] = []   # 批量更新
        processed = 0
        hit_count = 0

        for cid, pid in campaign_keys:
            # ── 步骤 1：聚合该 campaign 下所有 ASIN 的产品字段 ──
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

            # ── 步骤 2：拿产品字段去匹配策略 ──
            tz = campaign_meta.get((cid, pid), {}).get("timezone", "")
            targeting_type = campaign_meta.get((cid, pid), {}).get("targeting_type", "auto")
            existing = existing_map.get((cid, pid))

            if existing is None:
                # 情况 A：新 campaign → 必须命中策略才创建记录
                result = match_strategy_against_product(pid, assorts, labels, uids, strategies)
                if not result:
                    continue

                # 计算时间：先按 dayOfWeek/calendar 过滤，再取所有时段合并
                matched_strategy = next(
                    (s for s in strategies if s.id == result["strategy_id"]), None,
                )
                ts = te = ts_cn = te_cn = None
                if matched_strategy:
                    segments = (matched_strategy.time_settings or {}).get("segments", [])
                    filtered = _filter_segments_for_today(segments, matched_strategy.time_mode)
                    if filtered:
                        seg_times = [
                            _calc_strategy_times(
                                matched_strategy,
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
                    is_callback=TimePricingHitStatus.NO,
                    is_manual_rules=ManualRulesStatus.NO,
                    manual_rule_id="",
                    rule_updated_today=True,
                    created_at=now,
                    updated_at=now,
                ))
                processed += 1
                hit_count += 1
                continue

            # 情况 B：已有记录
            if existing.is_time_pricing == TimePricingHitStatus.YES:
                continue  # 正在分时，不更新
            if existing.rule_updated_today:
                continue  # 当天已更新，不重复

            # 优先级最高：用户手动设置的规则
            if existing.is_manual_rules == ManualRulesStatus.YES and existing.manual_rule_id:
                user_strategy = next(
                    (s for s in strategies if str(s.id) == str(existing.manual_rule_id)), None,
                )
                # 用户手动规则也支持多时段合并
                if user_strategy:
                    existing.hit_time_pricing_rules = existing.manual_rule_id
                    existing.rule_updated_today = True
                    existing.is_callback = TimePricingHitStatus.NO
                    existing.is_time_pricing = TimePricingHitStatus.NO
                    segments = (user_strategy.time_settings or {}).get("segments", [])
                    filtered = _filter_segments_for_today(segments, user_strategy.time_mode)
                    if filtered:
                        seg_times = [
                            _calc_strategy_times(
                                user_strategy,
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
                    update_records.append(existing)
                    processed += 1
                    hit_count += 1
                    continue
                # 手动规则的 ID 无效（不存在或已暂停）→ 降级为自动匹配，继续往下

            # 情况 C：自动重新命中并更新已有记录
            result = match_strategy_against_product(pid, assorts, labels, uids, strategies)
            existing.hit_time_pricing_rules = str(result["strategy_id"]) if result else ""
            existing.rule_updated_today = True
            # 新一天重新命中，重置分时和回调状态
            existing.is_callback = TimePricingHitStatus.NO
            existing.is_time_pricing = TimePricingHitStatus.NO
            if result:
                matched_strategy = next(
                    (s for s in strategies if s.id == result["strategy_id"]), None,
                )
                if matched_strategy:
                    segments = (matched_strategy.time_settings or {}).get("segments", [])
                    filtered = _filter_segments_for_today(segments, matched_strategy.time_mode)
                    if filtered:
                        seg_times = [
                            _calc_strategy_times(
                                matched_strategy,
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

    # ── Phase 3：执行线程 + 批量写入 ─────────────────────────────────────

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
                "hit_time_pricing_rules", "rule_updated_today",
                "time_start", "time_end", "time_start_cn", "time_end_cn",
                "is_callback", "is_time_pricing",
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
