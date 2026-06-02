"""广告活动 → 产品画像查询服务（campaign_product_service）。

提供从广告活动 ID + Profile ID 到关联产品字段（归类/标签/负责人）的标准查询链路，
供分时策略匹配、自动竞价规则等模块复用。

查询链路：
  1. campaign_id + profile_id → LxSpAd → ASIN 列表
  2. ASIN → LxProductInfo → assort / label / principal_list(uid)
  3. 扁平化去重 → 统一返回
"""
from __future__ import annotations

import json
from typing import Any

from api_v1.models.lingxing.ads.basic.lx_sp_ad import LxSpAd
from api_v1.models.lingxing.sales.listing.lx_product_info import LxProductInfo


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

def _parse_json_field(raw_val: str, target_set: set[str]) -> None:
    """解析字段值（可能是 JSON 数组字符串或纯文本），提取独立值加入集合。"""
    if not raw_val:
        return
    try:
        parsed = json.loads(raw_val)
    except (json.JSONDecodeError, TypeError):
        target_set.add(str(raw_val).strip())
        return
    if isinstance(parsed, list):
        for item in parsed:
            if item and str(item).strip():
                target_set.add(str(item).strip())
    else:
        target_set.add(str(raw_val).strip())


def _extract_principal_uids(principal_list: Any) -> list[int]:
    """从 principal_list 字段中提取所有 uid。

    principal_list 格式：[{"uid": 10390386, "realname": "陈慧瑩"}, ...]
    兼容 JSON 字符串和已解析的 Python list。
    """
    if not principal_list:
        return []
    if isinstance(principal_list, str):
        try:
            principal_list = json.loads(principal_list)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(principal_list, list):
        return []
    return [
        item["uid"] for item in principal_list
        if isinstance(item, dict) and "uid" in item
    ]


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

    products = LxProductInfo.objects.filter(asin__in=asins)
    if not products.exists():
        return {"assorts": [], "labels": [], "principal_uids": []}

    assorts: set[str] = set()
    labels: set[str] = set()
    principal_uids: set[int] = set()

    for p in products:
        for field_name, target in [("assort", assorts), ("label", labels)]:
            val = getattr(p, field_name, "")
            if val:
                _parse_json_field(val, target)
        for uid in _extract_principal_uids(p.principal_list):
            principal_uids.add(uid)

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
