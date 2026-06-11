"""SP 广告优化策略——主编排服务（optimization_strategy_service）。

职责：扫描所有开启的广告活动，用 LxAdRule 规则组进行五步串联匹配，
      写入 SpAdOptimizationStrategy 记录。

批量预加载 → 多线程并行匹配 → 批量写入，参照 ad_time_pricing_service.py 模式。
"""
from __future__ import annotations

import json as _json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.db import connections
from django.db.models import Q
from django.utils import timezone as dj_timezone

from api_v1.models.lingxing.ads.basic.lx_ads_profile import AdsProfileStatus, LxAdsProfile
from api_v1.models.lingxing.ads.basic.lx_sp_ad import LxSpAd
from api_v1.models.lingxing.ads.basic.lx_sp_campaign import LxSpCampaign
from api_v1.models.lingxing.ads.basic.lx_sp_target import LxSpTarget, SpTargetExpressionType
from api_v1.models.lingxing.ads.lx_ad_rule import AdRuleStatus, LxAdRule
from api_v1.models.lingxing.ads.lx_ad_rule_group import LxAdRuleGroup
from api_v1.models.lingxing.sales.listing.lx_product_info import LxProductInfo
from api_v2.models.sp_ad_optimization_strategy import (
    ManualRulesStatus,
    SpAdOptimizationStrategy,
)
from api_v2.services.ad_optimization.campaign_rule_matcher import match_rules_for_campaign

logger = logging.getLogger(__name__)

# 多线程并发数
MAX_WORKERS = 4


# ============================================================
# 辅助函数：字段解析
# ============================================================

def _parse_str_or_json_field(raw_val: Any) -> list[str]:
    """解析字段值（JSON 数组字符串或纯文本），返回扁平化值列表。

    复用自 ad_time_pricing_service.py 的同名工具函数。

    Args:
        raw_val: 原始字段值，可能是 JSON 字符串、列表或纯文本

    Returns:
        扁平化后的字符串值列表
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

    复用自 ad_time_pricing_service.py 的同名工具函数。

    Args:
        principal_list: LxProductInfo.principal_list 的原始值

    Returns:
        去重后的 uid 整数列表
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


def _parse_creation_date(raw_val: Any) -> date | None:
    """将 campaign 的 creation_date（毫秒时间戳）转换为 date 对象。

    兼容 int / str / None 三种形式。

    Args:
        raw_val: creation_date 字段的原始值

    Returns:
        成功则返回 date 对象，失败返回 None
    """
    if raw_val is None:
        return None
    try:
        ts_ms = int(raw_val)
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=dt_timezone.utc).date()
    except (ValueError, OSError, TypeError):
        logger.warning(
            "[_parse_creation_date] 无效时间戳: %s", raw_val,
        )
        return None


# ============================================================
# Phase 1：数据预加载
# ============================================================

def _load_campaigns() -> tuple[
    list[dict[str, Any]],
    dict[tuple[int, int], dict[str, Any]],
]:
    """加载所有启用广告活动并预加载产品字段。

    Returns:
        (campaigns, fields_map)：
        campaigns——[{"campaign_id": int, "profile_id": int,
                       "targeting_type": str, "creation_date": date|None}]
        fields_map——{(campaign_id, profile_id):
                      {"assorts": [], "labels": [], "uids": [],
                       "auto_targeting_groups": []}}
    """
    # 1. 加载启用且有时区的 campaign
    campaigns_raw = list(
        LxSpCampaign.objects.filter(state="enabled")
        .values_list("campaign_id", "profile_id", "targeting_type", "creation_date")
    )

    # 获取有效店铺
    profile_ids = list({pid for _, pid, _, _ in campaigns_raw})
    valid_profile_ids: set[int] = set(
        LxAdsProfile.objects.filter(
            profile_id__in=profile_ids,
            status=AdsProfileStatus.ENABLED,
        ).values_list("profile_id", flat=True)
    )

    # 过滤并构建 campaign 列表
    campaigns: list[dict[str, Any]] = []
    campaign_keys: set[tuple[int, int]] = set()
    for cid, pid, tt, cd in campaigns_raw:
        if pid not in valid_profile_ids:
            continue
        campaigns.append({
            "campaign_id": cid,
            "profile_id": pid,
            "targeting_type": tt or "auto",
            "creation_date": _parse_creation_date(cd),
        })
        campaign_keys.add((cid, pid))

    logger.info("[process_optimization_strategies] 有效 campaign=%d", len(campaigns))

    # 2. 批量加载广告（ASIN 映射）
    campaign_to_asins: dict[tuple[int, int], set[str]] = defaultdict(set)
    all_asins: set[str] = set()
    BATCH_SIZE = 500
    campaign_list = list(campaign_keys)
    for i in range(0, len(campaign_list), BATCH_SIZE):
        q_filter = Q()
        for cid, pid in campaign_list[i:i + BATCH_SIZE]:
            q_filter |= Q(campaign_id=cid, profile_id=pid)
        for ad in LxSpAd.objects.filter(q_filter).only(
            "campaign_id", "profile_id", "asin",
        ):
            if ad.asin:
                key = (ad.campaign_id, ad.profile_id)
                campaign_to_asins[key].add(ad.asin)
                all_asins.add(ad.asin)

    logger.info("[process_optimization_strategies] 有广告的 campaign=%d, ASIN=%d",
                len(campaign_to_asins), len(all_asins))

    # 3. 批量加载产品字段
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
    logger.info("[process_optimization_strategies] 产品画像 ASIN=%d", len(asin_to_fields))

    # 4. 批量加载自动定位组（仅 auto campaign）
    auto_campaign_keys = [
        k for k in campaign_keys
        if any(
            c["campaign_id"] == k[0] and c["profile_id"] == k[1]
            and c["targeting_type"] == "auto"
            for c in campaigns
        )
    ]
    campaign_targeting_groups: dict[tuple[int, int], list[str]] = defaultdict(list)
    if auto_campaign_keys:
        BATCH_SIZE = 500
        for i in range(0, len(auto_campaign_keys), BATCH_SIZE):
            q_filter = Q()
            for cid, pid in auto_campaign_keys[i:i + BATCH_SIZE]:
                q_filter |= Q(campaign_id=cid, profile_id=pid)
            # 只取 expression_type="auto" 的目标
            for target in LxSpTarget.objects.filter(
                q_filter,
                expression_type=SpTargetExpressionType.AUTO,
            ).only("campaign_id", "profile_id", "expression"):
                expr = target.expression or []
                if isinstance(expr, list):
                    for item in expr:
                        if isinstance(item, dict):
                            expr_type = item.get("type", "")
                            if expr_type:
                                campaign_targeting_groups[
                                    (target.campaign_id, target.profile_id)
                                ].append(expr_type)
        logger.info("[process_optimization_strategies] 定位组命中 campaign=%d",
                    len(campaign_targeting_groups))

    # 5. 按 campaign 聚合字段
    fields_map: dict[tuple[int, int], dict[str, Any]] = {}
    for c in campaigns:
        key = (c["campaign_id"], c["profile_id"])
        asins = campaign_to_asins.get(key, set())
        assorts: list[str] = []
        labels: list[str] = []
        uids: list[int] = []
        seen_assorts: set[str] = set()
        seen_labels: set[str] = set()
        seen_uids: set[int] = set()
        for asin in asins:
            fields = asin_to_fields.get(asin)
            if not fields:
                continue
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

        atg = campaign_targeting_groups.get(key, [])
        atg_unique: list[str] = list({t for t in atg if t})

        fields_map[key] = {
            "assorts": assorts,
            "labels": labels,
            "uids": uids,
            "auto_targeting_groups": atg_unique,
        }

    return campaigns, fields_map


# ============================================================
# Phase 2：加载规则组和规则
# ============================================================

def _load_rules_by_group() -> list[tuple[LxAdRuleGroup, list[LxAdRule]]]:
    """加载所有规则组，按 weight ASC / created_at DESC 排序，
    每组内按 rule_order 展开已启用的规则。

    Returns:
        [(LxAdRuleGroup, [LxAdRule, ...]), ...]
        仅包含至少有一条有效规则的组
    """
    groups = list(LxAdRuleGroup.objects.all().order_by("weight", "-created_at"))
    if not groups:
        return []

    # 收集所有被引用的规则 ID
    all_rule_ids: set[int] = set()
    for g in groups:
        for rid in (g.rule_order or []):
            try:
                all_rule_ids.add(int(rid))
            except (ValueError, TypeError):
                continue

    if not all_rule_ids:
        return []

    # 批量加载已启用的规则
    active_rules_map: dict[int, LxAdRule] = {}
    for rule in LxAdRule.objects.filter(
        id__in=list(all_rule_ids),
        status=AdRuleStatus.ACTIVE,
    ):
        active_rules_map[rule.id] = rule

    # 按组组装
    rules_by_group: list[tuple[LxAdRuleGroup, list[LxAdRule]]] = []
    for group in groups:
        ordered_rules: list[LxAdRule] = []
        for rid in (group.rule_order or []):
            try:
                rule_id = int(rid)
            except (ValueError, TypeError):
                continue
            rule = active_rules_map.get(rule_id)
            if rule is not None:
                ordered_rules.append(rule)
        if ordered_rules:
            rules_by_group.append((group, ordered_rules))

    logger.info("[process_optimization_strategies] 规则组=%d, 有效规则=%d",
                len(rules_by_group), len(active_rules_map))
    return rules_by_group


# ============================================================
# Phase 3：加载已有策略记录
# ============================================================

def _load_existing_strategies(
    campaign_pairs: list[tuple[int, int]],
) -> dict[tuple[int, int, str], SpAdOptimizationStrategy]:
    """按 campaign 范围查询已有 SpAdOptimizationStrategy 记录。

    Args:
        campaign_pairs: 有效的 (campaign_id, profile_id) 列表

    Returns:
        {(campaign_id, profile_id, targeting_type): SpAdOptimizationStrategy}
    """
    if not campaign_pairs:
        return {}

    cids = list({cid for cid, _ in campaign_pairs})
    pids = list({pid for _, pid in campaign_pairs})

    existing_map: dict[tuple[int, int, str], SpAdOptimizationStrategy] = {}
    for record in SpAdOptimizationStrategy.objects.filter(
        campaign_id__in=cids,
        profile_id__in=pids,
    ).iterator():
        existing_map[
            (record.campaign_id, record.profile_id, record.targeting_type)
        ] = record

    logger.info("[process_optimization_strategies] 已有策略记录=%d", len(existing_map))
    return existing_map


# ============================================================
# Phase 3 辅助：构建策略记录
# ============================================================

def _build_strategy_record(
    campaign: dict[str, Any],
    matched_rules: list[dict[str, Any]],
    existing: SpAdOptimizationStrategy | None,
    now: datetime,
) -> SpAdOptimizationStrategy | None:
    """根据匹配结果与已有记录状态构建 SpAdOptimizationStrategy 实例。

    处理四种场景：
      1. 新建：写入 auto_rules，is_manual_rules=否
      2. 已存在 + 手动未过期：auto_rules 置空，保持手动
      3. 已存在 + 手动已过期：降级为自动，重写 auto_rules
      4. 已存在 + 非手动：正常更新 auto_rules

    Args:
        campaign: campaign 信息字典
        matched_rules: 匹配到的规则列表（auto_rules 格式）
        existing: 已有策略记录（可为 None）
        now: 当前时间

    Returns:
        需要写入的 SpAdOptimizationStrategy 实例，无需更新时返回 None
    """
    cid = campaign["campaign_id"]
    pid = campaign["profile_id"]
    tt = campaign["targeting_type"]

    if existing is None:
        # 场景 1：新建
        return SpAdOptimizationStrategy(
            campaign_id=cid,
            profile_id=pid,
            targeting_type=tt,
            auto_rules=matched_rules,
            manual_rules=[],
            is_manual_rules=ManualRulesStatus.NO,
            manual_rules_expiry=None,
            rule_updated_today=True,
            created_at=now,
            updated_at=now,
        )

    # 场景 2：手动规则
    if existing.is_manual_rules == ManualRulesStatus.YES:
        expiry = existing.manual_rules_expiry
        if expiry is None or expiry > now:
            # 手动未过期：auto_rules 置空，仍保持手动
            existing.auto_rules = []
            existing.rule_updated_today = True
            existing.updated_at = now
            return existing
        # 手动已过期：降级为自动
        existing.is_manual_rules = ManualRulesStatus.NO
        existing.manual_rules = []
        existing.manual_rules_expiry = None
        existing.auto_rules = matched_rules
        existing.rule_updated_today = True
        existing.updated_at = now
        return existing

    # 场景 3 / 4：非手动，正常更新
    existing.auto_rules = matched_rules
    existing.rule_updated_today = True
    existing.updated_at = now
    return existing


# ============================================================
# Phase 4：多线程调度
# ============================================================

def _process_chunk(
    chunk_campaigns: list[dict[str, Any]],
    fields_map: dict[tuple[int, int], dict[str, Any]],
    rules_by_group: list[tuple[LxAdRuleGroup, list[LxAdRule]]],
    existing_map: dict[tuple[int, int, str], SpAdOptimizationStrategy],
) -> dict[str, Any]:
    """线程入口：处理一批 campaign，收集新建与更新记录。

    对每个 campaign 调用规则匹配器 → 构建策略记录 → 收集结果。

    Args:
        chunk_campaigns: 本线程负责的 campaign 列表
        fields_map: 预聚合的产品字段映射（共享读）
        rules_by_group: 预加载的规则组列表（共享读）
        existing_map: 已有策略记录映射（共享读）

    Returns:
        {"new_records": [], "update_records": [], "processed": int, "matched": int}
    """
    connections.close_all()

    new_records: list[SpAdOptimizationStrategy] = []
    update_records: list[SpAdOptimizationStrategy] = []
    processed = 0
    matched = 0
    now = dj_timezone.now()
    today = now.date()

    for campaign in chunk_campaigns:
        cid = campaign["campaign_id"]
        pid = campaign["profile_id"]
        key = (cid, pid)
        fields = fields_map.get(key)
        if not fields:
            continue

        # 匹配规则
        auto_rules = match_rules_for_campaign(
            profile_id=pid,
            targeting_type=campaign["targeting_type"],
            campaign_creation_date=campaign["creation_date"],
            product_assorts=fields["assorts"],
            product_labels=fields["labels"],
            product_uids=fields["uids"],
            auto_targeting_groups=fields["auto_targeting_groups"],
            rules_by_group=rules_by_group,
            today=today,
        )

        existing = existing_map.get((cid, pid, campaign["targeting_type"]))
        record = _build_strategy_record(campaign, auto_rules, existing, now)
        if record is None:
            continue

        processed += 1
        if record.pk is not None:
            # pk 存在表示已有记录（由 existing 修改得来）
            update_records.append(record)
        else:
            # pk 不存在 → 新建
            new_records.append(record)
        if auto_rules:
            matched += 1

    return {
        "new_records": new_records,
        "update_records": update_records,
        "processed": processed,
        "matched": matched,
    }


# ============================================================
# 主流程
# ============================================================

def process_optimization_strategies() -> dict[str, Any]:
    """SP 广告优化策略匹配主流程。

    1. 加载所有启用的 campaign 及产品字段
    2. 加载规则组及启用的规则
    3. 多线程并行匹配
    4. 批量写入 SpAdOptimizationStrategy

    Returns:
        {
            "total_campaigns": int,   # 扫描的 campaign 总数
            "matched": int,           # 有命中规则的 campaign 数
            "written": int,           # 写入记录总数（新建+更新）
            "new_records": int,       # 新建记录数
            "updated_records": int,   # 更新记录数
            "errors": list[str],      # 异常信息列表
        }
    """
    # Phase 1：数据预加载
    campaigns, fields_map = _load_campaigns()
    total_campaigns = len(campaigns)
    if not campaigns:
        return {
            "total_campaigns": 0,
            "matched": 0,
            "written": 0,
            "new_records": 0,
            "updated_records": 0,
            "errors": [],
        }

    # Phase 2：加载规则
    rules_by_group = _load_rules_by_group()
    if not rules_by_group:
        logger.warning("[process_optimization_strategies] 无可用规则组，跳过匹配")
        return {
            "total_campaigns": total_campaigns,
            "matched": 0,
            "written": 0,
            "new_records": 0,
            "updated_records": 0,
            "errors": [],
        }

    # Phase 3：加载已有记录
    campaign_pairs = [(c["campaign_id"], c["profile_id"]) for c in campaigns]
    existing_map = _load_existing_strategies(campaign_pairs)

    # Phase 4：多线程并行匹配
    chunk_size = max(1, len(campaigns) // MAX_WORKERS)
    chunks = [
        campaigns[i:i + chunk_size]
        for i in range(0, len(campaigns), chunk_size)
    ]
    chunks = chunks[:MAX_WORKERS]  # 最多 MAX_WORKERS 个线程

    all_new: list[SpAdOptimizationStrategy] = []
    all_updates: list[SpAdOptimizationStrategy] = []
    total_processed = 0
    total_matched = 0
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        futures = {
            executor.submit(
                _process_chunk,
                chunk,
                fields_map,
                rules_by_group,
                existing_map,
            ): idx
            for idx, chunk in enumerate(chunks)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                all_new.extend(result["new_records"])
                all_updates.extend(result["update_records"])
                total_processed += result["processed"]
                total_matched += result["matched"]
            except Exception as e:
                msg = f"chunk {idx} 处理异常: {e}"
                logger.exception("[process_optimization_strategies] %s", msg)
                errors.append(msg)

    # Phase 5：批量写入
    written = 0
    try:
        if all_new:
            SpAdOptimizationStrategy.objects.bulk_create(all_new, batch_size=500)
            written += len(all_new)
            logger.info("[process_optimization_strategies] 新建=%d", len(all_new))

        if all_updates:
            update_fields = [
                "auto_rules",
                "manual_rules",
                "is_manual_rules",
                "manual_rules_expiry",
                "rule_updated_today",
                "updated_at",
            ]
            SpAdOptimizationStrategy.objects.bulk_update(
                all_updates, update_fields, batch_size=500,
            )
            written += len(all_updates)
            logger.info("[process_optimization_strategies] 更新=%d", len(all_updates))
    except Exception as e:
        msg = f"批量写入异常: {e}"
        logger.exception("[process_optimization_strategies] %s", msg)
        errors.append(msg)

    return {
        "total_campaigns": total_campaigns,
        "matched": total_matched,
        "written": written,
        "new_records": len(all_new),
        "updated_records": len(all_updates),
        "errors": errors,
    }
