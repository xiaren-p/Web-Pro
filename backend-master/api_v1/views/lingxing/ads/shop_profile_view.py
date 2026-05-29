"""店铺配置数据视图（ShopProfile）。"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import LxCampaignInfo, LxShopProfile
from api_v1.utils.responses import drf_ok
from api_v1.views.lingxing.ads._helpers import COUNTRY_MAP


class ShopProfileViewSet(viewsets.ViewSet):
    """店铺配置数据视图。"""

    @action(detail=False, methods=["post"], url_path="options")
    def options(self, request: Request) -> Response:
        """获取店铺、国家、竞价策略下拉选项数据。

        Args:
            request (Request): DRF 原始请求对象。

        Returns:
            Response: 包含以下字段：

            - countries: 去重后的国家映射列表。
            - profiles: 店铺别名列表。
            - bidding_types: 广告基础表中实际出现过的竞价策略列表。
        """
        # 竞价策略中文映射，用于将原始英文 key 转换为可读 label
        BIDDING_TYPE_LABEL: dict[str, str] = {
            "legacyForSales": "动态竞价-只降低",
            "autoForSales": "动态竞价-提高和降低",
            "manual": "固定竞价",
            "ruleBased": "基于规则的竞价",
        }

        qs = LxShopProfile.objects.all()
        profiles: list[dict[str, str]] = []
        countries_set: set[str] = set()

        for item in qs:
            if item.profile_id:
                label = item.alias if item.alias else item.profile_id
                profiles.append({"value": str(item.profile_id), "label": label})
            if item.country:
                countries_set.add(item.country)

        countries = []
        for c in countries_set:
            c_name = COUNTRY_MAP.get(c.upper(), c)
            countries.append({"value": c, "label": c_name})

        # 从广告活动表中查出实际存在的竞价策略值（去重、排除空值）
        raw_bidding_types = (
            LxCampaignInfo.objects
            .exclude(bidding_type__isnull=True)
            .exclude(bidding_type="")
            .values_list("bidding_type", flat=True)
            .distinct()
        )
        bidding_types = [
            {"value": bt, "label": BIDDING_TYPE_LABEL.get(bt, bt)}
            for bt in raw_bidding_types
        ]

        return drf_ok({
            "countries": countries,
            "profiles": profiles,
            "bidding_types": bidding_types,
        })

