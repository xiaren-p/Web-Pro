"""广告配置下拉数据视图（店铺/国家/竞价策略）。

提供广告模块所需的店铺档案（profile）列表、国家下拉选项
以及竞价策略枚举值，供前端筛选组件使用。
"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.ads.models.lx_ads_profile import LxAdsProfile
from apps.ads.sp.models.lx_sp_campaign import LxSpCampaign
from apps.lingxing_basic.models.lx_shops import LxShops
from apps.common.utils.responses import drf_ok
from apps.ads.views._helpers import BIDDING_STRATEGY_LABEL


class ProfileOptionsViewSet(viewsets.ViewSet):
    """店铺配置下拉数据视图。

    返回广告模块所需的店铺档案列表、国家列表及竞价策略列表，
    聚合 LxAdsProfile、LxShops、LxSpCampaign 三张表的数据。
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="options")
    def options(self, request: Request) -> Response:
        """获取店铺、国家、竞价策略下拉选项数据。

        国家中文名不再使用硬编码 COUNTRY_MAP，改为从 LxShops.country 字段取值，
        通过 LxAdsProfile.sid → LxShops.sid 关联得到每条 profile 对应的国家中文名称。

        Args:
            request: DRF 原始请求对象。

        Returns:
            包含以下字段的响应：

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
