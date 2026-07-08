"""广告活动 → 产品画像查询服务（campaign_product_service）。

提供从广告活动 ID + Profile ID 到关联产品字段（归类/标签/负责人）的标准查询链路，
供分时策略匹配、自动竞价规则等模块复用。

查询链路：
  1. campaign_id + profile_id → LxSpAd → ASIN 列表
  2. ASIN → LxListingData + LxListingMeta + LxListingTag → 分类/标签/负责人
  3. 扁平化去重 → 统一返回
"""
from __future__ import annotations

from typing import Any

from apps.ads.sp.models.lx_sp_ad import LxSpAd
from apps.ads.sp.services.listing_fields_loader import load_asin_product_fields


# ============================================================
# 步骤 1：campaign → 广告投放 → ASIN 列表
# ============================================================

def get_asins_by_campaign(campaign_id: int, profile_id: int) -> list[str]:
    """根据广告活动 ID + Profile ID 获取关联的所有 ASIN。

    Args:
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID

    Returns:
        去重后的 ASIN 字符串列表，无匹配时返回空列表。
    """
    asins = (
        LxSpAd.objects
        .filter(campaign_id=campaign_id, profile_id=profile_id)
        .values_list("asin", flat=True)
        .distinct()
    )
    return [a for a in asins if a]


# ============================================================
# 步骤 2：ASIN → 产品信息（assort / label / principal_uids）
# ============================================================

def get_product_fields_by_asins(asins: list[str]) -> dict[str, list[str | int]]:
    """根据 ASIN 列表获取扁平化去重后的产品字段。

    Args:
        asins: ASIN 字符串列表

    Returns:
        {
            "assorts": [str],         # 扁平化去重后的归类列表
            "labels": [str],          # 扁平化去重后的标签列表
            "principal_uids": [int],  # 扁平化去重后的负责人 uid 列表
        }
    """
    if not asins:
        return {"assorts": [], "labels": [], "principal_uids": []}

    asin_fields = load_asin_product_fields(set(asins))
    assorts: set[str] = set()
    labels: set[str] = set()
    principal_uids: set[int] = set()

    for fields in asin_fields.values():
        assorts.update(fields.get("assorts", []))
        labels.update(fields.get("labels", []))
        principal_uids.update(fields.get("principal_uids", []))

    return {
        "assorts": sorted(assorts),
        "labels": sorted(labels),
        "principal_uids": sorted(principal_uids),
    }


# ============================================================
# 步骤 3：组合步骤 1+2，一步获取完整的 campaign 产品画像
# ============================================================

def get_campaign_product_profile(campaign_id: int, profile_id: int) -> dict[str, Any] | None:
    """获取广告活动关联的完整产品画像。

    组合步骤 1（campaign → ASIN）和步骤 2（ASIN → 产品字段）。

    Args:
        campaign_id: 广告活动 ID
        profile_id: 店铺 Profile ID

    Returns:
        {"asins": [str], "assorts": [str], "labels": [str], "principal_uids": [int]}
        若无法匹配到 ASIN 则返回 None。
    """
    asins = get_asins_by_campaign(campaign_id, profile_id)
    if not asins:
        return None
    fields = get_product_fields_by_asins(asins)
    return {"asins": asins, **fields}
