"""分时回调执行器（time_pricing_callback）。

职责：
  1. 遍历 AdTimePricingHit 中正在分时的记录（is_time_pricing=YES）
  2. 判断当前时段是否已离开分时区间
  3. 基于 LxSpKeyword/LxSpTarget 当前竞价 + callback_settings 计算回调竞价
  4. 写入 SpBidAdjustment（execution_type=TIME_PRICING_CALLBACK，bid_before 留空）
  5. 更新 AdTimePricingHit.is_time_pricing=NO

回调策略类型（来自 strategy.callback_settings）：
  - "multiplier": 当前竞价 × multiplier
  - "fixed": 固定值
  - "previous": 保持当前竞价不变
  - "none": 不做任何调整，仅标记 is_time_pricing=NO
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone as dt_timezone
from typing import Any


from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy, StrategyStatus
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices, ExecutionStatusChoices, ExecutionTypeChoices, SpBidAdjustment,
)
from api_v2.services.ad_rules.campaign_product_service import (
    get_asins_by_campaign, get_product_fields_by_asins,
)
from api_v2.services.ad_rules.strategy_matcher import match_strategy_against_product
from api_v2.services.ad_rules.time_pricing_executor import (
    _build_item_map, _find_matching_rules, _get_ad_items,
)

logger = logging.getLogger(__name__)


# ============================================================
# 回调竞价计算
# ============================================================

def _calc_callback_bid(current_bid: float, callback_settings: dict) -> float | None:
    """基于 LxSpKeyword/LxSpTarget 的当前竞价计算回调竞价。

    Args:
        current_bid: 投放项的当前竞价（直接从 LxSpKeyword/LxSpTarget.bid 读取）
        callback_settings: strategy.callback_settings

    Returns:
        回调后竞价；若策略为 none 则返回 None（不调整）
    """
    cb_type = callback_settings.get("type", "none")
    if cb_type == "multiplier":
        mul = float(callback_settings.get("multiplier", 1.0) or 1.0)
        return current_bid * mul
    if cb_type == "fixed":
        return float(callback_settings.get("fixed", current_bid) or current_bid)
    if cb_type == "previous":
        return current_bid
    return None


# ============================================================
# 单条记录的回调处理（拆分自主流程，控制函数 ≤50 行）
# ============================================================

def _process_callback_for_hit(
    hit: AdTimePricingHit,
    strategy: LxTimePricingStrategy,
    item_map: dict[tuple[int, int], list[dict[str, Any]]],
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
) -> bool:
    """处理单条命中记录的回调逻辑。

    若已离开分时时段，按回调策略计算并收集 SpBidAdjustment 记录。

    Args:
        hit: 待处理的命中记录
        strategy: 对应的分时策略
        item_map: 投放项内存映射
        now_utc: 当前 UTC 时间
        adjustments: 调整记录收集列表（引用传递，追加到此）

    Returns:
        True 表示已执行回调（is_time_pricing 应置 NO），False 表示仍在时段内不处理
    """
    if _find_matching_rules(strategy.time_settings or {}, hit.timezone or "", strategy.time_mode):
        return False  # 仍在分时时段

    callback = strategy.callback_settings or {}
    cb_type = callback.get("type", "none")
    items = _get_ad_items(hit.campaign_id, hit.profile_id, hit.targeting_type, item_map)

    if not items or cb_type == "none":
        return True  # 无投放项或不回调，直接标记结束

    for item in items:
        callback_bid = _calc_callback_bid(item["bid"], callback)
        if callback_bid is None:
            continue
        is_target = item["item_type"] == "target"
        adjustments.append(SpBidAdjustment(
            target_id=item["item_id"] if is_target else None,
            keyword_id=item["item_id"] if not is_target else None,
            campaign_id=hit.campaign_id,
            profile_id=hit.profile_id,
            execution_type=ExecutionTypeChoices.TIME_PRICING_CALLBACK,
            time_pricing_rule_id=strategy.id,
            auto_rule_id=None,
            is_time_pricing=TimePricingHitStatus.NO,
            bid_before=None,
            bid_after=callback_bid,
            adjustment_status=AdjustmentStatusChoices.PENDING,
            adjustment_time=now_utc,
            execution_status=ExecutionStatusChoices.PENDING,
        ))
    return True


def _preload_callback_data(
    hits: list[AdTimePricingHit],
) -> tuple[dict[tuple[int, int], list[dict[str, Any]]], dict[int, LxTimePricingStrategy]]:
    """批量预加载回调所需的投放项和策略数据。

    Args:
        hits: 待处理的命中记录列表

    Returns:
        (item_map, strategy_map) 元组
        - item_map: (campaign_id, profile_id) → 投放项列表
        - strategy_map: strategy_id → LxTimePricingStrategy
    """
    all_keys = {(h.campaign_id, h.profile_id) for h in hits}
    item_map = _build_item_map(all_keys)
    strategy_ids = {int(h.hit_time_pricing_rules) for h in hits if h.hit_time_pricing_rules}
    strategy_map = {
        s.id: s
        for s in LxTimePricingStrategy.objects.filter(pk__in=strategy_ids)
    }
    logger.info("[time_pricing_callback] 预加载: items=%d strategies=%d", len(item_map), len(strategy_map))
    return item_map, strategy_map


# ============================================================
# 回调后重新命中策略
# ============================================================

def _re_match_strategy(hit: AdTimePricingHit) -> None:
    """回调后重新命中分时策略，更新 hit_time_pricing_rules。

    优先级：
      1. 若用户手动设置了 user_manual_time_rules → 直接写入 hit_time_pricing_rules
      2. 否则重新执行 campaign → ASIN → 产品 → 策略命中链

    Args:
        hit: 刚完成回调的命中记录
    """
    manual_rules = hit.user_manual_time_rules
    if manual_rules and isinstance(manual_rules, list) and len(manual_rules) > 0:
        first = manual_rules[0]
        hit.hit_time_pricing_rules = str(first) if isinstance(first, (int, str)) else ""
        hit.hit_auto_bid_rules = ""
        hit.save(update_fields=["hit_time_pricing_rules", "hit_auto_bid_rules", "updated_at"])
        logger.info("[time_pricing_callback] campaign=%d 使用手动规则: %s", hit.campaign_id, hit.hit_time_pricing_rules)
        return

    try:
        asins = get_asins_by_campaign(hit.campaign_id, hit.profile_id)
        if not asins:
            hit.hit_time_pricing_rules = ""
            hit.hit_auto_bid_rules = ""
            hit.save(update_fields=["hit_time_pricing_rules", "hit_auto_bid_rules", "updated_at"])
            return

        fields = get_product_fields_by_asins(asins)
        strategies = list(
            LxTimePricingStrategy.objects
            .filter(status=StrategyStatus.ACTIVE)
            .order_by("weight", "-created_at")
        )
        result = match_strategy_against_product(
            profile_id=hit.profile_id,
            product_assorts=fields["assorts"],
            product_labels=fields["labels"],
            product_uids=fields["principal_uids"],
            strategies=strategies,
        )
        hit.hit_time_pricing_rules = str(result["strategy_id"]) if result else ""
        hit.hit_auto_bid_rules = ""
        hit.save(update_fields=["hit_time_pricing_rules", "hit_auto_bid_rules", "updated_at"])
        logger.info("[time_pricing_callback] campaign=%d 重新命中: time=%s", hit.campaign_id, hit.hit_time_pricing_rules)

    except Exception:
        logger.exception("[time_pricing_callback] campaign=%d 重新命中异常", hit.campaign_id)
        # 命中失败不阻塞主流程，record 保持上一次的规则


# ============================================================
# 主流程
# ============================================================

def _process_callback_chunk(
    hit_chunk: list[AdTimePricingHit],
    strategy_map: dict[int, LxTimePricingStrategy],
    item_map: dict,
    now_utc: datetime,
) -> tuple[list[SpBidAdjustment], list[AdTimePricingHit], int, int, list[str]]:
    """线程入口：处理一批命中记录的回调逻辑（纯内存计算，不查 DB）。"""
    adjustments: list[SpBidAdjustment] = []
    hits_to_update: list[AdTimePricingHit] = []
    processed = 0
    called_back = 0
    errors: list[str] = []

    for hit in hit_chunk:
        try:
            strategy = strategy_map.get(int(hit.hit_time_pricing_rules))
            if not strategy:
                hit.is_time_pricing = TimePricingHitStatus.NO
                hits_to_update.append(hit)
                processed += 1
                continue
            if not _process_callback_for_hit(hit, strategy, item_map, now_utc, adjustments):
                continue
            hit.is_time_pricing = TimePricingHitStatus.NO
            hits_to_update.append(hit)
            called_back += 1
            processed += 1
        except Exception:
            logger.exception("[time_pricing_callback] campaign=%d", hit.campaign_id)
            errors.append(f"campaign={hit.campaign_id} profile={hit.profile_id}")

    return adjustments, hits_to_update, processed, called_back, errors


def execute_time_pricing_callback() -> dict[str, Any]:
    """执行"分时回调"：遍历正在分时的记录，离开时段则回调竞价并重置 is_time_pricing。

    Returns:
        {
            "processed": int,    # 已处理的记录数（含跳过和无操作的）
            "called_back": int,  # 实际执行回调的记录数
            "errors": list[str], # 异常信息列表
        }
    """
    hits = list(AdTimePricingHit.objects.filter(is_time_pricing=TimePricingHitStatus.YES))
    if not hits:
        logger.info("[time_pricing_callback] 无正在分时的记录")
        return {"processed": 0, "called_back": 0, "errors": []}

    logger.info("[time_pricing_callback] 正在分时记录数=%d", len(hits))
    item_map, strategy_map = _preload_callback_data(hits)

    now_utc = datetime.now(dt_timezone.utc)
    CHUNKS = 16
    chunk_size = max(1, len(hits) // CHUNKS)
    chunks = [hits[i:i + chunk_size] for i in range(0, len(hits), chunk_size)][:CHUNKS]

    adjustments: list[SpBidAdjustment] = []
    hits_to_update: list[AdTimePricingHit] = []
    processed = 0
    called_back = 0
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=CHUNKS) as executor:
        futures = [executor.submit(_process_callback_chunk, c, strategy_map, item_map, now_utc) for c in chunks]
        for f in as_completed(futures):
            adjs, htus, pr, cb, errs = f.result()
            adjustments.extend(adjs)
            hits_to_update.extend(htus)
            processed += pr
            called_back += cb
            errors.extend(errs)

    _write_batch(adjustments, hits_to_update)

    for hit in hits_to_update:
        _re_match_strategy(hit)

    logger.info("[time_pricing_callback] 完成 processed=%d called_back=%d errors=%d", processed, called_back, len(errors))
    return {"processed": processed, "called_back": called_back, "errors": errors}


def _write_batch(
    adjustments: list[SpBidAdjustment],
    hits_to_update: list[AdTimePricingHit],
) -> None:
    """批量写入调整记录和命中状态。

    Args:
        adjustments: 待写入的 SpBidAdjustment 列表
        hits_to_update: 待写入的 AdTimePricingHit 列表
    """
    if adjustments:
        SpBidAdjustment.objects.bulk_create(adjustments, batch_size=500)
    if hits_to_update:
        AdTimePricingHit.objects.bulk_update(hits_to_update, ["is_time_pricing", "updated_at"], batch_size=500)
