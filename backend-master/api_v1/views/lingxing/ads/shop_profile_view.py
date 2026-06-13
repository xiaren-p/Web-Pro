"""广告通用店铺配置下拉数据视图（LxAdsProfile）。"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import LxAdsProfile, LxSpCampaign
from api_v1.utils.responses import drf_ok
from api_v1.views.lingxing.ads._helpers import BIDDING_STRATEGY_LABEL, COUNTRY_MAP


class ShopProfileViewSet(viewsets.ViewSet):
    """店铺配置下拉数据视图。"""

    @action(detail=False, methods=["post"], url_path="options")
    def options(self, request: Request) -> Response:
        """获取店铺、国家、竞价策略下拉选项数据。

        Args:
            request (Request): DRF 原始请求对象。

        Returns:
            Response: 包含以下字段：

            - countries: 去重后的国家映射列表。
            - profiles: 店铺名称列表。
            - bidding_types: 广告活动表中实际出现过的竞价策略列表（label 由后端统一映射）。
        """
        # ── 店铺列表（启用状态的账号）──
        profiles: list[dict[str, str]] = []
        countries_set: set[str] = set()

        for item in LxAdsProfile.objects.filter(status=1):
            if item.profile_id:
                label = item.name if item.name else str(item.profile_id)
                profiles.append({"value": str(item.profile_id), "label": label})
            if item.country_code:
                countries_set.add(item.country_code)

        countries = []
        for c in countries_set:
            c_name = COUNTRY_MAP.get(c.upper(), c)
            countries.append({"value": c, "label": c_name})

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
            "profiles": profiles,
            "bidding_types": bidding_types,
        })