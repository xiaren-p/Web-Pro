"""Listing 产品字段批量加载器。
统一从 LxListingData + LxListingMeta + LxListingTag 获取产品画像（分类/标签/负责人），替代已弃用的 LxProductInfo。
"""
from __future__ import annotations

from typing import Any
from collections import defaultdict

from apps.sales.listing.models.lx_listing_data import LxListingData
from apps.sales.listing.models.lx_listing_meta import LxListingMeta
from apps.sales.listing.models.lx_listing_tag import LxListingTag


def load_asin_product_fields(
    asin_set: set[str],
) -> dict[str, dict[str, list[Any]]]:
    """按 ASIN 批量加载产品字段：assorts / labels / principal_uids。

    数据源：
        - 分类(assorts)：LxListingMeta.assort（通过 listing_data__asin 关联）
        - 标签(labels)：LxListingData.global_tags → tagName 优先，空则用 LxListingTag 查 tag_name
        - 负责人(uids)：LxListingData.principal_info → principal_uid

    Args:
        asin_set: 待查询的 ASIN 集合

    Returns:
        {asin: {"assorts": [...], "labels": [...], "principal_uids": [...]}}
    """
    if not asin_set:
        return {}

    asin_list = list(asin_set)

    # ── 分类：LxListingMeta ──
    asin_to_assorts: dict[str, set[str]] = defaultdict(set)
    meta_qs = (
        LxListingMeta.objects
        .filter(listing_data__asin__in=asin_list)
        .select_related("listing_data")
        .only("assort", "listing_data__asin")
    )
    for meta in meta_qs.iterator(chunk_size=2000):
        asin = getattr(meta.listing_data, "asin", None)
        if asin and meta.assort:
            asin_to_assorts[asin].add(meta.assort)

    # ── 标签 + 负责人：LxListingData ──
    asin_to_labels: dict[str, set[str]] = defaultdict(set)
    asin_to_uids: dict[str, set[int]] = defaultdict(set)
    tag_ids_to_resolve: set[str] = set()
    # 记录哪些 ASIN 有 tagName 为空的标签（避免二次全表扫描）
    asin_tag_ids: dict[str, set[str]] = defaultdict(set)

    listings = (
        LxListingData.objects
        .filter(asin__in=asin_list)
        .only("asin", "global_tags", "principal_info")
    )
    for row in listings.iterator(chunk_size=2000):
        asin = row.asin
        # 标签
        for tag in (row.global_tags or []):
            if isinstance(tag, dict):
                name = tag.get("tagName") or ""
                if name:
                    asin_to_labels[asin].add(name)
                else:
                    tid = str(tag.get("globalTagId") or tag.get("id") or "")
                    if tid:
                        tag_ids_to_resolve.add(tid)
                        asin_tag_ids[asin].add(tid)
        # 负责人
        for p in (row.principal_info or []):
            if isinstance(p, dict):
                uid = p.get("principal_uid") or p.get("uid")
                if uid:
                    asin_to_uids[asin].add(int(uid))

    # ── 标签 ID → name 批量解析 ──
    if tag_ids_to_resolve:
        tag_name_map: dict[str, str] = {}
        for t in LxListingTag.objects.filter(
            global_tag_id__in=list(tag_ids_to_resolve),
            status="normal",
        ).values_list("global_tag_id", "tag_name").iterator(chunk_size=2000):
            tag_name_map[str(t[0])] = t[1] or ""
        # 回填：只需处理有空白标签的 ASIN
        for asin, tids in asin_tag_ids.items():
            for tid in tids:
                name = tag_name_map.get(tid, "")
                if name:
                    asin_to_labels[asin].add(name)

    # ── 组装结果 ──
    all_asins = set(asin_to_assorts) | set(asin_to_labels) | set(asin_to_uids)
    result: dict[str, dict[str, list[Any]]] = {}
    for asin in all_asins:
        result[asin] = {
            "assorts": list(asin_to_assorts.get(asin, set())),
            "labels": list(asin_to_labels.get(asin, set())),
            "principal_uids": list(asin_to_uids.get(asin, set())),
        }
    return result
