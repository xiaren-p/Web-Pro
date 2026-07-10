"""广告通用店铺配置下拉数据视图（LxAdsProfile）。"""
from __future__ import annotations

from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.ads.models.lx_ads_profile import LxAdsProfile
from apps.ads.sp.models.lx_sp_campaign import LxSpCampaign
from apps.sales.listing.models.lx_listing_data import LxListingData
from apps.sales.listing.models.lx_listing_tag import LxListingTag
from apps.lingxing_basic.models.lx_shops import LxShops
from apps.ads.utils.ad_status import _LABEL_MAP as SERVICE_STATUS_LABEL
from apps.common.utils.responses import drf_ok
from apps.ads.views._helpers import (
    BIDDING_STRATEGY_LABEL,
    CAMPAIGN_TYPE_SHORT,
    KEYWORD_MATCH_TYPE_LABEL,
    NEGATIVE_MATCH_TYPE_LABEL,
    NEGATIVE_TYPE_LABEL,
)


def _flat_parse_label(raw_label: str) -> list[str]:
    """解析 LxProductInfo.label 字段，将其扁平化为标签字符串列表。

    label 字段存在两种格式：
    1. JSON 数组字符串，如 ``'["清仓", "夏季"]'`` 或 ``'["促销"]'``。
    2. 逗号分隔字符串，如 ``"清仓,夏季"``。

    本函数依次尝试 JSON 解析和逗号分隔解析。

    Args:
        raw_label (str): LxProductInfo.label 原始值。

    Returns:
        list[str]: 扁平化后的标签字符串列表。
    """
    import json

    if not raw_label:
        return []
    s = raw_label.strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    return [t.strip() for t in s.split(",") if t.strip()]


# ── 统一枚举标签注册表 ──
# 所有模块的枚举标签映射集中于此注册表，前端通过 POST /ads/enum-labels
# 传入 module 参数按需获取。新增模块只需追加条目，无需修改视图逻辑。
# 仅 tags 模块从 LxProductInfo.label 动态取值，其余模块仍为静态字典。
_ENUM_LABEL_REGISTRY: dict[str, dict[str, str]] = {
    "campaign_status": {
        "enabled": "已启用",
        "paused": "已暂停",
        "archived": "已归档",
    },
    "service_status": SERVICE_STATUS_LABEL,
    "bidding_strategy": BIDDING_STRATEGY_LABEL,
    "campaign_type": CAMPAIGN_TYPE_SHORT,
    "negative_match_type": NEGATIVE_MATCH_TYPE_LABEL,
    "keyword_match_type": KEYWORD_MATCH_TYPE_LABEL,
    "negative_type": NEGATIVE_TYPE_LABEL,
}


class ShopProfileViewSet(viewsets.ViewSet):
    """ShopProfileViewSet 视图集。"""
    permission_classes = [IsAuthenticated]
    """店铺配置下拉数据视图。"""

    @action(detail=False, methods=["post"], url_path="options")
    def options(self, request: Request) -> Response:
        """获取店铺、国家、竞价策略下拉选项数据。

        国家中文名不再使用硬编码 COUNTRY_MAP，改为从 LxShops.country 字段取值，
        通过 LxAdsProfile.sid → LxShops.sid 关联得到每条 profile 对应的国家中文名称。

        Args:
            request (Request): DRF 原始请求对象。

        Returns:
            Response: 包含以下字段：

            - countries: 去重后的国家列表（value 为 country_code，label 为 LxShops.country 中文名）。
            - profiles: 店铺名称列表。
            - bidding_types: 广告活动表中实际出现过的竞价策略列表（label 由后端统一映射）。
        """
        # ── 店铺列表（启用状态的账号）──
        sid_set: set[int] = set()
        profiles: list[dict[str, str]] = []

        for item in LxAdsProfile.objects.filter(status=1):
            if not item.profile_id:
                continue
            label = item.name if item.name else str(item.profile_id)
            profiles.append({
                "value": str(item.profile_id),
                "label": label,
                "country_code": item.country_code or "",
                "sid": item.sid or 0,
            })
            if item.sid:
                sid_set.add(item.sid)

        # ── 通过 LxAdsProfile.sid → LxShops.sid 关联到 LxShops.country ──
        sid_to_country: dict[int, str] = {}
        if sid_set:
            for shop in LxShops.objects.filter(sid__in=sid_set).only("sid", "country"):
                sid_to_country[shop.sid] = shop.country or ""

        # ── 为每个 profile 补上国家中文名 ──
        seen_countries: set[str] = set()
        countries: list[dict[str, str]] = []
        for sp in profiles:
            c_code = sp["country_code"]
            country_name = sid_to_country.get(sp["sid"], c_code)
            if c_code and c_code not in seen_countries:
                seen_countries.add(c_code)
                countries.append({"value": c_code, "label": country_name})

        # ── 竞价策略列表（从 LxSpCampaign.bidding JSONField 中提取 strategy 字段去重）──
        raw_bidding_types = list(
            set(
                LxSpCampaign.objects
                .filter(bidding__isnull=False)
                .exclude(bidding={})
                .values_list("bidding__strategy", flat=True)
            )
        )
        bidding_types = [
            {"value": bt, "label": BIDDING_STRATEGY_LABEL.get(bt, bt)}
            for bt in raw_bidding_types
            if bt
        ]

        return drf_ok({
            "countries": countries,
            "profiles": [
                {"value": sp["value"], "label": sp["label"], "country": sp["country_code"]}
                for sp in profiles
            ],
            "bidding_types": bidding_types,
        })

    @action(detail=False, methods=["post"], url_path="sku-options")
    def sku_options(self, request: Request) -> Response:
        """获取 SKU/ASIN/MSKU 搜索下拉选项数据。

        数据由 Celery 定时任务 ``refresh_listing_caches`` 预热到 Redis，
        搜索在内存中毫秒级过滤。
        """
        keyword = (request.data.get("keyword") or "").strip().lower()

        all_skus: list[dict] = cache.get("sku_options_cache_v1") or []

        if keyword:
            result = [s for s in all_skus
                      if keyword in str(s.get("value", "")).lower()
                      or keyword in str(s.get("code", "")).lower()
                      or keyword in str(s.get("title", "")).lower()]
        else:
            result = all_skus

        return drf_ok({"skus": result})

    @action(detail=False, methods=["post"], url_path="enum-labels")
    def enum_labels(self, request: Request) -> Response:
        """获取指定模块的枚举标签映射列表，供前端下拉组件按需拉取。

        通过 body 中的 ``module`` 参数区分模块。标签模块（tags）从
        LxProductInfo.label 动态取值（逗号分隔字符串 → 扁平化 → 去重），
        其余模块直接从内存注册表返回。

        Args:
            request (Request): DRF 请求对象，body 参数：

            - module (str): 模块标识，可选值见 _ENUM_LABEL_REGISTRY 及 "tags"。

        Returns:
            Response: ``labels`` 列表，每项为 {value, label}。
        """
        module = (request.data.get("module") or "").strip()
        if not module:
            return drf_ok({"labels": []}, msg="module 参数为必填")

        if module == "tags":
            _TAGS_CACHE_KEY = "shop_profile_view_tags_v1"
            tags = cache.get(_TAGS_CACHE_KEY)
            if tags is None:
                raw_tags: list[str] = list(
                    LxListingData.objects
                    .exclude(global_tags__isnull=True)
                    .exclude(global_tags=[])
                    .values_list("global_tags", flat=True)
                    .distinct()
                )
                all_tag_ids: set[str] = set()
                for raw in raw_tags:
                    if isinstance(raw, list):
                        for entry in raw:
                            if isinstance(entry, dict):
                                gid = str(entry.get("globalTagId") or "")
                                if gid:
                                    all_tag_ids.add(gid)
                tags = []
                if all_tag_ids:
                    tag_names = LxListingTag.objects.filter(
                        global_tag_id__in=list(all_tag_ids),
                        status="normal",
                    ).values_list("tag_name", flat=True).distinct()
                    tags = [{"value": tn, "label": tn} for tn in tag_names if tn]
                cache.set(_TAGS_CACHE_KEY, tags, 300)
            return drf_ok({"labels": tags})

        label_map = _ENUM_LABEL_REGISTRY.get(module)
        if label_map is None:
            return drf_ok({"labels": []}, msg=f"未知的枚举模块: {module}")

        labels = [{"value": k, "label": v} for k, v in label_map.items()]
        return drf_ok({"labels": labels})