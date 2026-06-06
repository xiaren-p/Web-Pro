"""分时竞价计算与写入工具（time_pricing_calculator）。

提供分时开始竞价计算、回调竞价计算、投放项分批查询和批量写入的通用逻辑。

注意：投放项按 (campaign_id, profile_id) 分批 Q 对象 SQL 查询，SQL 层过滤不走全表扫。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.db import transaction

from api_v1.models.lingxing.ads.basic.lx_sp_keyword import LxSpKeyword
from api_v1.models.lingxing.ads.basic.lx_sp_target import LxSpTarget
from api_v2.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices, ExecutionStatusChoices, ExecutionTypeChoices, SpBidAdjustment,
)

logger = logging.getLogger(__name__)

# 分时服务最大连续失败次数阈值（#10：退避机制）
MAX_ERROR_COUNT = 10


# ============================================================
# 竞价规则计算
# ============================================================

def calc_new_bid(current_bid: float, rule: dict) -> float | None:
    """根据单条规则计算调整后的竞价。

    Args:
        current_bid: 当前竞价
        rule: {"operateType", "operateValue", "limitValue", "triggerValue", "targetValue"}

    Returns:
        调整后竞价；bid_above/below 条件不满足时返回 None（不调整）
    """
    op = rule.get("operateType", "")
    val = float(rule.get("operateValue", 0) or 0)
    lim = float(rule.get("limitValue", 0) or 0)
    trig = float(rule.get("triggerValue", 0) or 0)
    tgt = float(rule.get("targetValue", 0) or 0)

    if op == "percent_decrease":
        return max(current_bid * (1 - val / 100), lim) if val else current_bid
    if op == "percent_increase":
        return min(current_bid * (1 + val / 100), lim) if val else current_bid
    if op == "fixed_decrease":
        return max(current_bid - val, lim)
    if op == "fixed_increase":
        return min(current_bid + val, lim)
    if op == "fixed":
        return val
    if op == "bid_above_fixed":
        return tgt if current_bid > trig else None
    if op == "bid_below_fixed":
        return tgt if current_bid < trig else None
    return None


def calc_reverse_bid(adjusted_bid: float, rule: dict) -> float | None:
    """根据单条降/涨规则反推调整前竞价（calc_new_bid 的逆运算）。

    回调时用于从已被降价的 DB 竞价逆推出分时前的原始竞价。
    注意：反推未考虑 limitValue 截断，结果仅作近似参考。

    Args:
        adjusted_bid: 规则调整后的竞价
        rule: {"operateType", "operateValue", ...}

    Returns:
        调整前竞价；除零上游或不可反推规则返回 None
    """
    op = rule.get("operateType", "")
    val = float(rule.get("operateValue", 0) or 0)

    if op == "percent_decrease":
        # forward: bid × (1 - val/100)，不低于 lim
        # reverse: bid ÷ (1 - val/100)
        # #8 除零保护：val >= 100 无法反推
        if val >= 100:
            return None
        if not val:
            return adjusted_bid
        return adjusted_bid / (1 - val / 100)
    if op == "percent_increase":
        # forward: bid × (1 + val/100)，不高于 lim
        # reverse: bid ÷ (1 + val/100)
        if not val:
            return adjusted_bid
        return adjusted_bid / (1 + val / 100)
    if op == "fixed_decrease":
        # forward: bid - val，不低于 lim
        # reverse: bid + val
        return adjusted_bid + val
    if op == "fixed_increase":
        # forward: bid + val，不高于 lim
        # reverse: bid - val
        return adjusted_bid - val
    if op in ("fixed", "bid_above_fixed", "bid_below_fixed"):
        # fixed 无条件替换；条件型无条件历史，均不可逆推
        return None
    return None


def calc_callback_bid(current_bid: float, callback_settings: dict) -> float | None:
    """根据回调策略计算恢复后的竞价。

    Args:
        current_bid: 投放项的基础竞价（应为反推后的原始竞价）
        callback_settings: strategy.callback_settings

    Returns:
        回调后竞价；type=none 时返回 None
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
# 投放项查询
# ============================================================

def build_item_map(
    campaign_keys: set[tuple[int, int]],
    batch_size: int = 500,
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """按 campaign_keys 精确查询投放项，SQL 层过滤，不扫全表。

    将 campaign_keys 按 batch_size 分批构建 Q 对象查询，
    避免单个 OR 超长 SQL，同时只返回命中的行。

    Args:
        campaign_keys: 需要查询的 (campaign_id, profile_id) 集合
        batch_size: 每批 OR 条件数上限

    Returns:
        {(cid, pid): [{"item_type", "item_id", "ad_group_id", "bid"}]}
    """
    from django.db.models import Q

    item_map: dict[tuple[int, int], list[dict[str, Any]]] = {}
    keys_list = list(campaign_keys)

    for offset in range(0, len(keys_list), batch_size):
        chunk = keys_list[offset:offset + batch_size]
        q = Q()
        for cid, pid in chunk:
            q |= Q(campaign_id=cid, profile_id=pid)

        for t in LxSpTarget.objects.filter(q, bid__isnull=False, state="enabled").iterator():
            key = (t.campaign_id, t.profile_id)
            item_map.setdefault(key, []).append({
                "item_type": "target",
                "item_id": t.target_id,
                "ad_group_id": t.ad_group_id,
                "bid": float(t.bid),
            })

        for k in LxSpKeyword.objects.filter(q, bid__isnull=False, state="enabled").iterator():
            key = (k.campaign_id, k.profile_id)
            item_map.setdefault(key, []).append({
                "item_type": "keyword",
                "item_id": k.keyword_id,
                "ad_group_id": k.ad_group_id,
                "bid": float(k.bid),
            })

    return item_map


def get_ad_items(
    campaign_id: int,
    profile_id: int,
    targeting_type: str,
    item_map: dict[tuple[int, int], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """从预加载的 item_map 中按 targeting_type 过滤投放项。

    Args:
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID
        targeting_type: 投放类型（auto=定位组, manual=关键词）

    Returns:
        [{"item_type": "target"/"keyword", "item_id": int, "ad_group_id": int, "bid": float}]
    """
    all_items = item_map.get((campaign_id, profile_id), [])
    if targeting_type == "auto":
        return [it for it in all_items if it["item_type"] == "target"]
    if targeting_type == "manual":
        return [it for it in all_items if it["item_type"] == "keyword"]
    return all_items


# ============================================================
# 写入工具
# ============================================================

def append_start_adjustment(
    item: dict[str, Any],
    campaign_id: int,
    profile_id: int,
    strategy_id: int,
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
) -> bool:
    """将单条投放项的竞价调整添加到收集列表。

    若 bid_after == bid（竞价不变），直接标 SUCCESS 不调 API。

    Args:
        item: {"item_type", "item_id", "bid", "bid_after"} 投放项数据
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID
        strategy_id: 命中策略 ID
        now_utc: 调整时间
        adjustments: 待批量写入的列表（引用传递）

    Returns:
        True 表示需要调 API，False 表示竞价不变直接标记成功
    """
    is_target = item["item_type"] == "target"
    bid_before = item.get("bid_before", item["bid"])
    bid_after = item.get("bid_after", item["bid"])

    if bid_before == bid_after:
        adjustments.append(SpBidAdjustment(
            target_id=item["item_id"] if is_target else None,
            keyword_id=item["item_id"] if not is_target else None,
            campaign_id=campaign_id,
            profile_id=profile_id,
            execution_type=ExecutionTypeChoices.TIME_PRICING_START,
            time_pricing_rule_id=strategy_id,
            auto_rule_id=None,
            is_time_pricing=TimePricingHitStatus.YES,
            bid_before=bid_before,
            bid_after=bid_after,
            adjustment_status=AdjustmentStatusChoices.SUCCESS,
            adjustment_time=now_utc,
            execution_status=ExecutionStatusChoices.SUCCESS,
            msg="分时竞价前与竞价后竞价相等，无需调整",
            updated_at=now_utc,
        ))
        return False

    adjustments.append(SpBidAdjustment(
        target_id=item["item_id"] if is_target else None,
        keyword_id=item["item_id"] if not is_target else None,
        campaign_id=campaign_id,
        profile_id=profile_id,
        execution_type=ExecutionTypeChoices.TIME_PRICING_START,
        time_pricing_rule_id=strategy_id,
        auto_rule_id=None,
        is_time_pricing=TimePricingHitStatus.YES,
        bid_before=bid_before,
        bid_after=bid_after,
        adjustment_status=AdjustmentStatusChoices.PENDING,
        adjustment_time=now_utc,
        execution_status=ExecutionStatusChoices.PENDING,
        updated_at=now_utc,
    ))
    return True


def append_callback_adjustment(
    item: dict[str, Any],
    callback_bid: float,
    campaign_id: int,
    profile_id: int,
    strategy_id: int,
    now_utc: datetime,
    adjustments: list[SpBidAdjustment],
) -> bool:
    """将单条投放项的回调竞价调整添加到收集列表。

    回调竞价 == item["bid"]（数据库竞价）时直接标 SUCCESS，不调 API。
    不等时写 PENDING CALLBACK 记录。

    Args:
        item: {"item_type", "item_id", "bid"} 投放项数据
        callback_bid: 回调目标竞价
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID
        strategy_id: 命中策略 ID
        now_utc: 调整时间
        adjustments: 待批量写入的列表（引用传递）

    Returns:
        True 表示写了 PENDING 记录（需调 API），False 表示竞价不变标 SUCCESS
    """
    current_bid = item["bid"]
    is_target = item["item_type"] == "target"

    if round(callback_bid, 4) == round(current_bid, 4):
        adjustments.append(SpBidAdjustment(
            target_id=item["item_id"] if is_target else None,
            keyword_id=item["item_id"] if not is_target else None,
            campaign_id=campaign_id,
            profile_id=profile_id,
            execution_type=ExecutionTypeChoices.TIME_PRICING_CALLBACK,
            time_pricing_rule_id=strategy_id,
            auto_rule_id=None,
            is_time_pricing=TimePricingHitStatus.NO,
            bid_before=None,
            bid_after=callback_bid,
            adjustment_status=AdjustmentStatusChoices.SUCCESS,
            adjustment_time=now_utc,
            execution_status=ExecutionStatusChoices.SUCCESS,
            msg="回调竞价与数据库竞价相等，无需调整",
            updated_at=now_utc,
        ))
        return False

    adjustments.append(SpBidAdjustment(
        target_id=item["item_id"] if is_target else None,
        keyword_id=item["item_id"] if not is_target else None,
        campaign_id=campaign_id,
        profile_id=profile_id,
        execution_type=ExecutionTypeChoices.TIME_PRICING_CALLBACK,
        time_pricing_rule_id=strategy_id,
        auto_rule_id=None,
        is_time_pricing=TimePricingHitStatus.NO,
        bid_before=None,
        bid_after=callback_bid,
        adjustment_status=AdjustmentStatusChoices.PENDING,
        adjustment_time=now_utc,
        execution_status=ExecutionStatusChoices.PENDING,
        updated_at=now_utc,
    ))
    return True


# ============================================================
# 回调必要性判断（#7：用实际 START 记录替代反推估算）
# ============================================================

def has_successful_start_adjustment(
    campaign_id: int,
    profile_id: int,
) -> bool:
    """检查该 campaign 是否有成功执行的分时开始（START）调整记录。

    用于 _do_callback 中判断降价是否真正生效过——如果从未成功降价，
    则无需写回调记录。这比 calc_reverse_bid 反推更准确，因为反推不考虑
    limitValue 截断和 API 实际执行结果。

    Args:
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID

    Returns:
        True 表示该 campaign 至少有一条降价成功执行的记录
    """
    return SpBidAdjustment.objects.filter(
        campaign_id=campaign_id,
        profile_id=profile_id,
        execution_type=ExecutionTypeChoices.TIME_PRICING_START,
        execution_status=ExecutionStatusChoices.SUCCESS,
    ).exists()


# ============================================================
# 批量写入（#3：事务保护）
# ============================================================

@transaction.atomic
def write_batch(
    adjustments: list[SpBidAdjustment],
    hits_to_update: list[AdTimePricingHit],
) -> None:
    """批量写入调整记录和命中状态（事务保护）。

    两步操作在同一事务中：全部成功或全部回滚，防止 SpBidAdjustment
    写入后崩溃导致 AdTimePricingHit 状态不一致。

    Args:
        adjustments: 待写入的 SpBidAdjustment 列表
        hits_to_update: 待更新 awaiting_start/is_time_pricing 的记录列表
    """
    if adjustments:
        SpBidAdjustment.objects.bulk_create(adjustments, batch_size=500)
    if hits_to_update:
        AdTimePricingHit.objects.bulk_update(
            hits_to_update,
            [
                "awaiting_start",
                "is_time_pricing",
                "is_callback",
                "rule_updated_today",
                "hit_time_pricing_rules",
                "error_count",
                "updated_at",
            ],
            batch_size=500,
        )
