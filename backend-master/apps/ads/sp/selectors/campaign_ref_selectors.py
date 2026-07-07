"""SP 广告活动参考数据查询选择器。

提供 profile_map / country_map / rate_map / listing_caches 等只读缓存查询。
供 ``ad_campaign_view`` 与 ``listing_cache_refresh_task`` 共用。
"""
from typing import Any

from django.core.cache import cache as _cache

from apps.ads.models.lx_ads_profile import LxAdsProfile
from apps.ads.sp.models.lx_sp_ad import LxSpAd
from apps.sales.listing.models.lx_listing_data import LxListingData
from apps.sales.models.lx_shops import LxShops
from apps.sales.models.lx_exchange_rate import LxExchangeRate
from apps.ads.views._helpers import parse_exchange_rate

_REF_TTL = 600


def get_profile_map() -> dict[str, dict[str, str]]:
    """profile_id → {profile_alias, country_code, sid} 全量缓存。

    Returns:
        dict[str, dict[str, str]]: profile_id 字符串 → 属性字典。
    """
    _key = "sp_ref_profile_map_v3"
    cached = _cache.get(_key)
    if cached is not None:
        return cached
    result: dict[str, dict[str, str]] = {}
    for p in LxAdsProfile.objects.all().values("profile_id", "name", "country_code", "currency_code", "sid"):
        result[str(p["profile_id"])] = {
            "profile_alias": p["name"] or str(p["profile_id"]),
            "country_code": p["country_code"] or "",
            "currency_code": p["currency_code"] or "",
            "sid": str(p["sid"] or ""),
        }
    _cache.set(_key, result, _REF_TTL)
    return result


def get_sid_country_map() -> dict[int, str]:
    """sid → 中文国家名 全量缓存。

    Returns:
        dict[int, str]: sid → 国家名称。
    """
    _key = "sp_ref_sid_country_v2"
    cached = _cache.get(_key)
    if cached is not None:
        return cached
    result: dict[int, str] = {}
    for shop in LxShops.objects.all().only("sid", "country"):
        if shop.sid:
            result[int(shop.sid)] = shop.country or ""
    _cache.set(_key, result, _REF_TTL)
    return result


def get_rate_map() -> dict[str, dict[str, Any]]:
    """currency_code → {icon, code, rate} 全量缓存（取每币种最新记录）。

    Returns:
        dict[str, dict[str, Any]]: 币种代码 → 汇率信息。
    """
    _key = "sp_ref_rate_map_v2"
    cached = _cache.get(_key)
    if cached is not None:
        return cached
    result: dict[str, dict[str, Any]] = {}
    for r in LxExchangeRate.objects.all().order_by("-date"):
        if r.code not in result:
            result[r.code] = {
                "icon": r.icon or "￥",
                "code": r.code,
                "rate": parse_exchange_rate(r.my_rate, r.rate_org),
            }
    _cache.set(_key, result, _REF_TTL)
    return result


def load_all_listing_caches() -> dict[str, Any]:
    """一次性全表扫描构建 listing 维度的 Redis 缓存（tag/owner/ASN映射）。

    Returns:
        dict[str, Any]: 含 status / tags_count / asins_count 等字段的执行摘要。
    """
    from django.core.cache import cache as _redis
    _all = list(LxListingData.objects.values(
        "asin", "global_tags", "principal_info",
    ))
    # SKU 下拉选项缓存：seller_sku 去重后的全量列表
    sku_qs = (
        LxListingData.objects
        .exclude(seller_sku="")
        .exclude(asin="")
        .values("seller_sku", "asin", "parent_asin", "item_name", "small_image_url")
    )
    sku_list: list[dict[str, str]] = []
    sku_seen: set[str] = set()
    for row in sku_qs.iterator(chunk_size=2000):
        key = row["seller_sku"]
        if key in sku_seen:
            continue
        sku_seen.add(key)
        sku_list.append({
            "value": key,
            "label": key,
            "code": row["asin"] or "",
            "title": row["item_name"] or "",
            "img": row["small_image_url"] or "",
            "parent": row["parent_asin"] or "",
        })
    _redis.set("sku_options_cache_v1", sku_list, _REF_TTL)

    ad_rows = list(LxSpAd.objects.values("asin", "campaign_id", "profile_id"))

    # sp_tag_asin_map_v2: tag_id → [asin, ...]
    tag_asin = {}
    for d in _all:
        tags = d.get("global_tags") or []
        for t in tags:
            tid = t.get("id") or t.get("globalTagId") or t
            if tid:
                tag_asin.setdefault(str(tid), []).append(d["asin"])
    for tid in tag_asin:
        tag_asin[tid] = list(set(tag_asin[tid]))

    # sp_owner_asin_map_v2: owner → [asin, ...]
    owner_asin = {}
    for d in _all:
        principals = d.get("principal_info") or []
        for p in principals:
            uid = p.get("principal_uid") or p.get("principal_name") or ""
            if uid:
                owner_asin.setdefault(str(uid), []).append(d["asin"])
    for uid in owner_asin:
        owner_asin[uid] = list(set(owner_asin[uid]))

    # sp_asin_tags_map_v2: asin → {tags: [...], owners: [...]}
    asin_tags = {}
    for d in _all:
        asin = d["asin"]
        tags = [t.get("id") or t.get("globalTagId") or t for t in (d.get("global_tags") or [])]
        owners = [p.get("principal_uid") or p.get("principal_name") or "" for p in (d.get("principal_info") or [])]
        asin_tags[asin] = {"tags": list(filter(None, tags)), "owners": list(filter(None, owners))}

    # sp_asin_cp_map_v2: asin → [(campaign_id, profile_id), ...]
    asin_cp = {}
    for a in ad_rows:
        asin_cp.setdefault(a["asin"], []).append((a["campaign_id"], a["profile_id"]))
    for asin in asin_cp:
        asin_cp[asin] = list(set(asin_cp[asin]))

    # sp_sku_cp_map_v2: not used currently but populated for completeness
    sku_cp = {}

    # sp_cp_asin_map_v2: (campaign_id, profile_id) → [asin, ...]
    cp_asin = {}
    for a in ad_rows:
        key = f"{a['campaign_id']}::{a['profile_id']}"
        cp_asin.setdefault(key, []).append(a["asin"])

    _redis.set("sp_tag_asin_map_v2", tag_asin, _REF_TTL)
    _redis.set("sp_owner_asin_map_v2", owner_asin, _REF_TTL)
    _redis.set("sp_asin_tags_map_v2", asin_tags, _REF_TTL)
    _redis.set("sp_asin_cp_map_v2", asin_cp, _REF_TTL)
    _redis.set("sp_sku_cp_map_v2", sku_cp, _REF_TTL)
    _redis.set("sp_cp_asin_map_v2", cp_asin, _REF_TTL)

    return {
        "status": "done",
        "tags_count": len(tag_asin),
        "owners_count": len(owner_asin),
        "asins_count": len(asin_tags),
        "sku_count": len(sku_list),
    }


def get_tag_asin_map() -> dict[str, list[str]]:
    """读取缓存的 tag_id → [asin, ...] 映射。"""
    from django.core.cache import cache as _redis
    return _redis.get("sp_tag_asin_map_v2") or {}


def get_owner_asin_map() -> dict[str, list[str]]:
    """读取缓存的 owner → [asin, ...] 映射。"""
    from django.core.cache import cache as _redis
    return _redis.get("sp_owner_asin_map_v2") or {}


def get_asin_info_map() -> dict[str, dict]:
    """读取缓存的 asin → {tags, owners} 映射。"""
    from django.core.cache import cache as _redis
    return _redis.get("sp_asin_tags_map_v2") or {}


def get_asin_cp_map() -> dict[str, list[tuple[int, int]]]:
    """读取缓存的 asin → [(campaign_id, profile_id), ...] 映射。"""
    from django.core.cache import cache as _redis
    return _redis.get("sp_asin_cp_map_v2") or {}


def get_sku_cp_map() -> dict[str, list[tuple[int, int]]]:
    """读取缓存的 sku → [(campaign_id, profile_id), ...] 映射。"""
    from django.core.cache import cache as _redis
    return _redis.get("sp_sku_cp_map_v2") or {}


def get_cp_asin_map() -> dict[str, list[str]]:
    """读取缓存的 (campaign_id, profile_id) → [asin, ...] 映射。"""
    from django.core.cache import cache as _redis
    return _redis.get("sp_cp_asin_map_v2") or {}
