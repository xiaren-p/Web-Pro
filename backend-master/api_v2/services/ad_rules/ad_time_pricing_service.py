"""广告分时策略命中服务（ad_time_pricing_service）。

职责：扫描新广告，匹配分时调价策略规则，写入命中记录。
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any

from api_v1.models.lingxing.ads.basic.lx_sp_ad import LxSpAd
from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy, StrategyStatus
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.services.ad_rules.campaign_product_service import (
    get_asins_by_campaign,
    get_product_fields_by_asins,
)

logger = logging.getLogger(__name__)


# ============================================================
# 分时策略匹配
# ============================================================

def _check_time_match(strategy: LxTimePricingStrategy) -> bool:
    """检查当前日期是否在策略生效时间范围内。

    策略的 start_month/day / end_month/day 为 null 表示不限。
    年份不限——仅比较月日，因此策略每年此时段生效。
    """
    today = date.today()

    sm = strategy.start_month
    sd = strategy.start_day
    em = strategy.end_month
    ed = strategy.end_day

    # 若四者均为 null → 不限时间，始终命中
    if sm is None and sd is None and em is None and ed is None:
        return True

    # 若部分为 null，视为不限（保守处理：半限定=不限那端）
    if sm is None or sd is None or em is None or ed is None:
        return True

    today_md = (today.month, today.day)
    start_md = (sm, sd)
    end_md = (em, ed)

    # 跨年情况（如 11月1日 ~ 3月1日）
    if start_md <= end_md:
        return start_md <= today_md <= end_md
    else:
        return today_md >= start_md or today_md <= end_md


def _check_field_match(
    strategy: LxTimePricingStrategy,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
) -> bool:
    """检查产品信息是否匹配策略的字段设置。

    策略的 categories / managers / tags 若为空或全选 → 视为不限。
    只要策略中有一个值与产品匹配即可。
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


def match_strategy(
    profile_id: int,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
) -> dict[str, Any] | None:
    """匹配分时调价策略。

    获取所有开启的策略，按权重升序（权重越小优先级越高）。
    首个全部规则命中的策略胜出。

    Args:
        profile_id: 店铺 Profile ID
        product_assorts: 产品归类列表
        product_labels: 产品标签列表
        product_uids: 产品负责人 uid 列表

    Returns:
        {"strategy_id": int, "strategy_name": str} 或 None
    """
    strategies = LxTimePricingStrategy.objects.filter(
        status=StrategyStatus.ACTIVE,
    ).order_by("weight", "-created_at")

    for s in strategies:
        # 规则 1：适用店铺
        shop_list: list = s.shops or []
        if shop_list and profile_id not in shop_list:
            continue

        # 规则 2：生效时间
        if not _check_time_match(s):
            continue

        # 规则 3：字段设置
        if not _check_field_match(s, product_assorts, product_labels, product_uids):
            continue

        return {
            "strategy_id": s.id,
            "strategy_name": s.name,
        }

    return None


# ============================================================
# 主流程：扫描新广告并命中策略
# ============================================================

def _process_single_campaign(cid: int, pid: int, existing_keys: set[tuple[int, int]]) -> tuple[list[AdTimePricingHit], int, int, str | None]:
    """处理单个 campaign 下的所有新广告，返回待写入的命中记录列表。

    在 ThreadPoolExecutor 中并行调用。

    Args:
        cid: campaign_id
        pid: profile_id
        existing_keys: 已存在的 (ad_id, profile_id) 集合

    Returns:
        (records, processed, hits, error_msg)
    """
    records: list[AdTimePricingHit] = []
    processed = 0
    hits = 0

    try:
        # 步骤 1+2：获取 ASIN 和产品画像（同 campaign 下所有广告共享）
        asins = get_asins_by_campaign(cid, pid)
        pinfo = None
        if asins:
            fields = get_product_fields_by_asins(asins)
            pinfo = {"asins": asins, **fields}

        # 获取该 campaign 下的广告
        ads = LxSpAd.objects.filter(campaign_id=cid, profile_id=pid)
        for ad in ads:
            ad_id = ad.ad_id

            # 已存在 → 跳过
            if (ad_id, pid) in existing_keys:
                continue

            processed += 1

            # 无 ASIN 或产品信息 → 写空记录
            if pinfo is None or not pinfo.get("asins"):
                records.append(AdTimePricingHit(
                    ad_id=ad_id, profile_id=pid,
                    is_time_pricing=TimePricingHitStatus.NO,
                ))
                continue

            # 匹配分时策略
            result = match_strategy(
                profile_id=pid,
                product_assorts=pinfo["assorts"],
                product_labels=pinfo["labels"],
                product_uids=pinfo["principal_uids"],
            )

            if result:
                records.append(AdTimePricingHit(
                    ad_id=ad_id, profile_id=pid,
                    hit_time_pricing_rules=result["strategy_name"],
                    is_time_pricing=TimePricingHitStatus.YES,
                ))
                hits += 1
            else:
                records.append(AdTimePricingHit(
                    ad_id=ad_id, profile_id=pid,
                    is_time_pricing=TimePricingHitStatus.NO,
                ))

        return (records, processed, hits, None)

    except Exception as e:
        return ([], processed, hits, f"campaign={cid}, profile={pid}: {e}")


def process_new_ads() -> dict[str, Any]:
    """扫描所有 LxSpCampaign，对其下新广告并行执行分时策略匹配。

    优化要点：
      1. 一次性预查所有已存在的 (ad_id, profile_id)，避免逐条 N+1 查询。
      2. 同 campaign 下的产品画像只计算一次，所有广告共享。
      3. 使用 ThreadPoolExecutor 并行处理各 campaign 的 I/O 密集型查询。
      4. 最终使用 bulk_create 批量写入，减少 DB 往返。

    Returns:
        {"total_campaigns": int, "new_ads_processed": int, "hits": int, "errors": [str]}
    """
    campaigns = LxSpCampaign.objects.all()
    total_campaigns = campaigns.count()

    # 预查所有已存在的 (ad_id, profile_id)
    existing_keys: set[tuple[int, int]] = set(
        AdTimePricingHit.objects.values_list("ad_id", "profile_id")
    )

    total_processed = 0
    total_hits = 0
    all_records: list[AdTimePricingHit] = []
    errors: list[str] = []

    # 确保每个线程有独立的 DB 连接（Django 默认线程局部连接）
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_process_single_campaign, camp.campaign_id, camp.profile_id, existing_keys): camp
            for camp in campaigns
        }
        for future in as_completed(futures):
            records, processed, hits, err = future.result()
            all_records.extend(records)
            total_processed += processed
            total_hits += hits
            if err:
                logger.error("[ad_time_pricing_service][process_new_ads] %s", err)
                errors.append(err)

    # 批量写入（close 后 DB 连接自动提交）
    if all_records:
        AdTimePricingHit.objects.bulk_create(all_records, batch_size=500)

    logger.info(
        "[ad_time_pricing_service][process_new_ads] 完成：campaigns=%d, new_ads=%d, hits=%d, errors=%d",
        total_campaigns, total_processed, total_hits, len(errors),
    )
    return {
        "total_campaigns": total_campaigns,
        "new_ads_processed": total_processed,
        "hits": total_hits,
        "errors": errors,
    }
