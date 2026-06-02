"""广告分时策略命中服务（ad_time_pricing_service）。

职责：扫描新广告，匹配分时调价策略规则，写入命中记录。
"""
from __future__ import annotations

import json as _json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from django.db import connections
from django.db.models import Q

from api_v1.models.lingxing.ads.basic.lx_sp_ad import LxSpAd
from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy, StrategyStatus
from api_v1.models.lingxing.sales.listing.lx_product_info import LxProductInfo
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.services.ad_rules.strategy_matcher import match_strategy_against_product

logger = logging.getLogger(__name__)


def match_strategy(
    profile_id: int,
    product_assorts: list[str],
    product_labels: list[str],
    product_uids: list[int],
) -> dict[str, Any] | None:
    """匹配分时调价策略（便捷封装，自动查库加载策略列表）。

    获取所有开启的策略，按权重升序，委托 strategy_matcher 匹配。

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
# 批量预加载工具函数（内存解析，无 DB 查询）
# ============================================================

def _parse_str_or_json_field(raw_val: Any) -> list[str]:
    """解析字段值（JSON 数组字符串或纯文本），返回扁平化值列表。

    用于解析 LxProductInfo 的 assort / label 等字段，
    与 campaign_product_service._parse_json_field 逻辑等价但返回列表。

    Args:
        raw_val: 可能是 JSON 字符串、纯文本字符串或 None/空。

    Returns:
        解析后的字符串列表（已去空去重）。
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

    格式：[{"uid": 10390386, "realname": "..."}, ...]
    兼容 JSON 字符串和已解析的 Python list。

    Args:
        principal_list: JSON 字符串或已解析的 list[dict]。

    Returns:
        uid 整数列表（去重）。
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
# 主流程：扫描新广告并命中策略（并行优化版）
# ============================================================

def process_new_ads() -> dict[str, Any]:
    """批量预加载 + 多线程并行扫描广告，匹配分时策略并写入命中记录。

    优化要点：
    - 批量查询：所有广告一次查询（分块 Q 过滤），所有产品一次查询，避免 N+1。
    - 并行匹配：ThreadPoolExecutor(max_workers=4) 按 campaign 并行，
      每线程先调用 connections.close_all() 以确保独立的 DB 连接。
    - 主线程收集所有线程结果后统一增量写入（每 500 条 bulk_create）。

    Returns:
        {
            "total_campaigns": int,   # LxSpCampaign 总数
            "new_ads_processed": int,  # 新扫描广告数（不在 existing_keys 中）
            "hits": int,              # 命中策略的广告数
            "written": int,           # 实际写入 AdTimePricingHit 的条数
            "errors": list[str],      # 异常信息列表
        }
    """
    MAX_WORKERS = 4
    BATCH_Q_SIZE = 500          # 每次 Q 构建包含的 OR 条件数
    FLUSH_BATCH_SIZE = 500      # 每攒满多少条即 bulk_create

    # ——————————————————————————————————————————————————————
    # Phase 1：主线程批量预加载所有数据，构建内存映射
    # ——————————————————————————————————————————————————————

    # 1a. 获取所有 campaign 的 (campaign_id, profile_id)
    campaign_pairs = list(
        LxSpCampaign.objects.values_list("campaign_id", "profile_id")
    )
    total_campaigns = len(campaign_pairs)
    logger.info("[process_new_ads] campaign 总数=%d", total_campaigns)

    if not campaign_pairs:
        logger.info("[process_new_ads] 无 campaign 数据，退出")
        return {
            "total_campaigns": 0,
            "new_ads_processed": 0,
            "hits": 0,
            "written": 0,
            "errors": [],
        }

    # 1b. 批量查询所有广告（分块 Q 构建，控制单条 SQL 大小）
    all_ads_raw: list[LxSpAd] = []
    for i in range(0, len(campaign_pairs), BATCH_Q_SIZE):
        batch_pairs = campaign_pairs[i:i + BATCH_Q_SIZE]
        q_filter = Q()
        for cid, pid in batch_pairs:
            q_filter |= Q(campaign_id=cid, profile_id=pid)
        all_ads_raw.extend(
            LxSpAd.objects.filter(q_filter)
            .only("campaign_id", "profile_id", "ad_id", "asin")
        )
    logger.info(
        "[process_new_ads] 广告批量查询完成：总数=%d（%d 批 Q 查询）",
        len(all_ads_raw),
        (len(campaign_pairs) + BATCH_Q_SIZE - 1) // BATCH_Q_SIZE,
    )

    # 1c. 构建 campaign_key -> 广告 映射 & 收集全部唯一 ASIN
    # campaign_key = (campaign_id, profile_id)
    campaign_to_ads: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    all_asins: set[str] = set()
    for ad in all_ads_raw:
        key = (ad.campaign_id, ad.profile_id)
        campaign_to_ads[key].append({"ad_id": ad.ad_id, "asin": ad.asin or ""})
        if ad.asin:
            all_asins.add(ad.asin)
    logger.info(
        "[process_new_ads] 有广告数据的 campaign=%d，唯一 ASIN=%d",
        len(campaign_to_ads), len(all_asins),
    )

    # 1d. 批量查询所有产品信息，构建 asin → 字段映射
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
    logger.info("[process_new_ads] 产品信息预加载完成，命中 ASIN=%d", len(asin_to_fields))

    # 1e. 预查所有已存在的命中记录 (campaign_id, profile_id)
    existing_keys: set[tuple[int, int]] = set(
        AdTimePricingHit.objects.values_list("campaign_id", "profile_id")
    )
    logger.info("[process_new_ads] 已有命中记录数=%d", len(existing_keys))

    # 1f. 预加载所有启用的策略（按权重升序，同权重按创建时间倒序）
    strategies: list[LxTimePricingStrategy] = list(
        LxTimePricingStrategy.objects
        .filter(status=StrategyStatus.ACTIVE)
        .order_by("weight", "-created_at")
    )
    logger.info("[process_new_ads] 启用策略数=%d", len(strategies))

    # ——————————————————————————————————————————————————————
    # Phase 2：多线程并行处理（仅内存匹配，无 DB 查询）
    # ——————————————————————————————————————————————————————

    # 筛选出有广告数据的 campaign 作为待处理列表
    campaign_list: list[tuple[int, int]] = [
        key for key in campaign_pairs if key in campaign_to_ads
    ]
    logger.info("[process_new_ads] 待处理 campaign 数=%d", len(campaign_list))

    if not campaign_list:
        logger.info("[process_new_ads] 无可处理 campaign（均无广告数据），退出")
        return {
            "total_campaigns": total_campaigns,
            "new_ads_processed": 0,
            "hits": 0,
            "written": 0,
            "errors": [],
        }

    # 将 campaign 列表均分为 MAX_WORKERS 份
    chunk_size = max(1, len(campaign_list) // MAX_WORKERS)
    chunks: list[list[tuple[int, int]]] = []
    for i in range(0, len(campaign_list), chunk_size):
        chunks.append(campaign_list[i:i + chunk_size])
    # 若因整除导致 chunk 数 > MAX_WORKERS，则将尾部合并到最后一份
    if len(chunks) > MAX_WORKERS:
        for extra in chunks[MAX_WORKERS:]:
            chunks[MAX_WORKERS - 1].extend(extra)
        chunks = chunks[:MAX_WORKERS]
    logger.info("[process_new_ads] 启动 %d 个线程，各负责 campaign 数=%s",
                len(chunks), [len(c) for c in chunks])

    def _process_campaign_chunk(
        campaign_keys: list[tuple[int, int]],
    ) -> dict[str, Any]:
        """子线程入口：处理一批 campaign，返回匹配结果列表。

        关键安全措施：
        - 入口处调用 connections.close_all() 确保每个线程拥有独立的 DB 连接。
        - 线程内不执行任何 ORM 查询，纯内存匹配。

        Args:
            campaign_keys: 本线程负责的 (campaign_id, profile_id) 列表。

        Returns:
            {"hits": list[AdTimePricingHit], "processed": int, "hit_count": int}
        """
        connections.close_all()

        thread_hits: list[AdTimePricingHit] = []
        thread_processed = 0
        thread_hit_count = 0

        for cid, pid in campaign_keys:
            ads = campaign_to_ads.get((cid, pid), [])
            if not ads:
                continue

            # 聚合该 campaign 下所有 ASIN 的产品字段（去重）
            merged_assorts: list[str] = []
            merged_labels: list[str] = []
            merged_uids: list[int] = []
            seen_a: set[str] = set()
            seen_b: set[str] = set()
            seen_u: set[int] = set()

            for ad in ads:
                asin = ad["asin"]
                if not asin:
                    continue
                fields = asin_to_fields.get(asin)
                if not fields:
                    continue
                for val in fields["assorts"]:
                    if val not in seen_a:
                        seen_a.add(val)
                        merged_assorts.append(val)
                for val in fields["labels"]:
                    if val not in seen_b:
                        seen_b.add(val)
                        merged_labels.append(val)
                for val in fields["principal_uids"]:
                    if val not in seen_u:
                        seen_u.add(val)
                        merged_uids.append(val)

            # campaign 粒度：已存在记录则跳过
            if (cid, pid) in existing_keys:
                continue
            thread_processed += 1

            # 匹配分时策略（以 campaign 下所有 ASIN 聚合后的产品字段为准）
            result = match_strategy_against_product(
                profile_id=pid,
                product_assorts=merged_assorts,
                product_labels=merged_labels,
                product_uids=merged_uids,
                strategies=strategies,
            )
            if result:
                thread_hits.append(AdTimePricingHit(
                    campaign_id=cid,
                    profile_id=pid,
                    hit_time_pricing_rules=str(result["strategy_id"]),
                    is_time_pricing=TimePricingHitStatus.NO,
                ))
                thread_hit_count += 1
            else:
                thread_hits.append(AdTimePricingHit(
                    campaign_id=cid,
                    profile_id=pid,
                    is_time_pricing=TimePricingHitStatus.NO,
                ))

        return {
            "hits": thread_hits,
            "processed": thread_processed,
            "hit_count": thread_hit_count,
        }

    # 启动线程池
    errors: list[str] = []
    all_results: list[AdTimePricingHit] = []
    total_processed = 0
    total_hits = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_chunk = {
            executor.submit(_process_campaign_chunk, chunk): idx
            for idx, chunk in enumerate(chunks)
        }
        for future in as_completed(future_to_chunk):
            chunk_idx = future_to_chunk[future]
            try:
                result = future.result()
                all_results.extend(result["hits"])
                total_processed += result["processed"]
                total_hits += result["hit_count"]
                logger.info(
                    "[process_new_ads] 线程 #%d 完成：processed=%d hits=%d records=%d",
                    chunk_idx, result["processed"], result["hit_count"],
                    len(result["hits"]),
                )
            except Exception as e:
                err_msg = f"线程 #{chunk_idx} 崩溃: {e}"
                logger.error("[process_new_ads] %s", err_msg, exc_info=True)
                errors.append(err_msg)

    # ——————————————————————————————————————————————————————
    # Phase 3：主线程统一增量写入（与原 _flush 行为一致）
    # ——————————————————————————————————————————————————————

    total_written = 0

    def _flush_batch(batch: list[AdTimePricingHit]) -> None:
        """批量写入一批记录，失败时降级为逐条写入。"""
        nonlocal total_written
        if not batch:
            return
        try:
            AdTimePricingHit.objects.bulk_create(batch, batch_size=FLUSH_BATCH_SIZE)
            total_written += len(batch)
            logger.debug(
                "[process_new_ads] 批量写入 %d 条，累计 %d 条",
                len(batch), total_written,
            )
        except Exception as e:
            logger.error("[process_new_ads] 批量写入失败: %s，降级逐条写入", e)
            for rec in batch:
                try:
                    rec.save()
                    total_written += 1
                except Exception as e2:
                    logger.error(
                        "[process_new_ads] 逐条写入失败 campaign=%d: %s", rec.campaign_id, e2,
                    )

    for i in range(0, len(all_results), FLUSH_BATCH_SIZE):
        _flush_batch(all_results[i:i + FLUSH_BATCH_SIZE])

    # ——————————————————————————————————————————————————————
    # 汇总日志与返回值
    # ——————————————————————————————————————————————————————

    logger.info(
        "[process_new_ads] 完成：campaigns=%d ads_loaded=%d new=%d hits=%d "
        "written=%d errors=%d",
        total_campaigns, len(all_ads_raw), total_processed, total_hits,
        total_written, len(errors),
    )
    return {
        "total_campaigns": total_campaigns,
        "new_ads_processed": total_processed,
        "hits": total_hits,
        "written": total_written,
        "errors": errors,
    }
