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
    _find_matching_rules, _get_ad_items,
)

logger = logging.getLogger(__name__)


# ============================================================
# 回调竞价计算
# ============================================================

def _calc_callback_bid(
    current_bid: float, callback_settings: dict,
) -> float | None:
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

    # "none"：不回调
    return None


# ============================================================
# 回调后重新命中策略
# ============================================================

def _re_match_strategy(hit: AdTimePricingHit) -> None:
    """回调后重新命中分时策略。

    优先级：
      1. 若用户手动设置了 user_manual_time_rules → 直接写入 hit_time_pricing_rules
      2. 否则重新执行 campaign → ASIN → 产品 → 策略命中链

    Args:
        hit: 刚完成回调的命中记录
    """
    # 1. 用户手动规则优先
    manual_rules = hit.user_manual_time_rules
    if manual_rules and isinstance(manual_rules, list) and len(manual_rules) > 0:
        first = manual_rules[0]
        hit.hit_time_pricing_rules = str(first) if isinstance(first, (int, str)) else ""
        hit.hit_auto_bid_rules = ""
        hit.save(update_fields=["hit_time_pricing_rules", "hit_auto_bid_rules", "updated_at"])
        logger.info(
            "[time_pricing_callback] campaign=%d 使用用户手动分时规则: %s",
            hit.campaign_id, hit.hit_time_pricing_rules,
        )
        return

    # 2. 自动命中：重新走命中链路
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
        logger.info(
            "[time_pricing_callback] campaign=%d 重新命中: time=%s",
            hit.campaign_id, hit.hit_time_pricing_rules,
        )

    except Exception as e:
        logger.error(
            "[time_pricing_callback] campaign=%d 重新命中异常: %s",
            hit.campaign_id, e, exc_info=True,
        )


# ============================================================
# 主流程
# ============================================================

def execute_time_pricing_callback() -> dict[str, Any]:
    """执行"分时回调"：遍历正在分时的记录，离开时段则回调竞价。

    对所有 is_time_pricing=YES 的记录，判断是否已离开分时时段，
    若离开则按策略 callback_settings 恢复竞价，并重置 is_time_pricing=NO。

    Returns:
        {"processed": int, "called_back": int, "errors": [str]}
    """
    hits = AdTimePricingHit.objects.filter(
        is_time_pricing=TimePricingHitStatus.YES,
    )
    if not hits.exists():
        logger.info("[time_pricing_callback] 无正在分时的记录")
        return {"processed": 0, "called_back": 0, "errors": []}

    logger.info("[time_pricing_callback] 正在分时记录数=%d", hits.count())

    processed = 0
    called_back = 0
    errors: list[str] = []

    for hit in hits:
        try:
            # 2. 加载命中的策略
            strategy_id = int(hit.hit_time_pricing_rules)
            strategy = LxTimePricingStrategy.objects.filter(pk=strategy_id).first()
            if not strategy:
                # 策略已被删除，清除分时状态 + 尝试重新命中
                hit.is_time_pricing = TimePricingHitStatus.NO
                hit.save(update_fields=["is_time_pricing", "updated_at"])
                _re_match_strategy(hit)
                processed += 1
                continue

            time_settings = strategy.time_settings or {}
            tz = hit.timezone or ""

            # 3. 判断当前时间是否仍在分时时段内
            still_in_period = len(_find_matching_rules(time_settings, tz)) > 0
            if still_in_period:
                # 仍在分时时段，不回调
                continue

            processed += 1

            # 4. 获取回调策略
            callback = strategy.callback_settings or {}
            cb_type = callback.get("type", "none")

            # 5. 查询投放项
            items = _get_ad_items(hit.campaign_id, hit.profile_id, hit.targeting_type)
            now_utc = datetime.now(dt_timezone.utc)

            if not items or cb_type == "none":
                # 无投放项或策略为不回调 → 直接标记分时结束 + 重新命中
                hit.is_time_pricing = TimePricingHitStatus.NO
                hit.save(update_fields=["is_time_pricing", "updated_at"])
                _re_match_strategy(hit)
                called_back += 1
                continue

            # 6. 对每个投放项：基于当前竞价（从 LxSpKeyword/LxSpTarget 取到的 bid）计算回调
            for item in items:
                item_id = item["item_id"]
                is_target = item["item_type"] == "target"
                current_bid = item["bid"]

                callback_bid = _calc_callback_bid(current_bid, callback)
                if callback_bid is None or callback_bid == current_bid:
                    continue

                SpBidAdjustment.objects.create(
                    target_id=item_id if is_target else None,
                    keyword_id=item_id if not is_target else None,
                    campaign_id=hit.campaign_id,
                    profile_id=hit.profile_id,
                    targeting_type=hit.targeting_type,
                    execution_type=ExecutionTypeChoices.TIME_PRICING_CALLBACK,
                    time_pricing_rule_id=strategy.id,
                    auto_rule_id=None,
                    is_time_pricing=TimePricingHitStatus.NO,
                    bid_before=None,
                    bid_after=callback_bid,
                    adjustment_status=AdjustmentStatusChoices.PENDING,
                    adjustment_time=now_utc,
                    execution_status=ExecutionStatusChoices.PENDING,
                )

            # 7. 重置分时状态 + 重新命中策略
            hit.is_time_pricing = TimePricingHitStatus.NO
            hit.save(update_fields=["is_time_pricing", "updated_at"])
            _re_match_strategy(hit)
            called_back += 1

        except Exception as e:
            err = f"campaign={hit.campaign_id} profile={hit.profile_id}: {e}"
            logger.error("[time_pricing_callback] %s", err, exc_info=True)
            errors.append(err)

    logger.info(
        "[time_pricing_callback] 完成 processed=%d called_back=%d errors=%d",
        processed, called_back, len(errors),
    )
    return {"processed": processed, "called_back": called_back, "errors": errors}
