"""枚举标签映射视图。

集中管理各模块（campaign_status / service_status / bidding_strategy 等）
的枚举标签映射，供前端下拉组件按 module 参数按需拉取。

标签模块（tags）从 LxProductInfo.label / global_tags 动态取值，
其余模块均使用静态注册表 _ENUM_LABEL_REGISTRY。
"""
from __future__ import annotations

from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.sales.listing.models.lx_listing_data import LxListingData
from apps.sales.listing.models.lx_listing_tag import LxListingTag
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
        raw_label: LxProductInfo.label 原始值。

    Returns:
        扁平化后的标签字符串列表。
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


class EnumLabelsViewSet(viewsets.ViewSet):
    """枚举标签映射视图集。

    提供统一的枚举标签查询入口，前端通过 POST 请求传入 ``module`` 参数
    获取对应模块的标签映射列表。标签模块（tags）动态从数据库读取，
    其余模块从内存注册表返回。
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="enum-labels")
    def enum_labels(self, request: Request) -> Response:
        """获取指定模块的枚举标签映射列表，供前端下拉组件按需拉取。

        通过 body 中的 ``module`` 参数区分模块。标签模块（tags）从
        LxProductInfo.label 动态取值（逗号分隔字符串 → 扁平化 → 去重），
        其余模块直接从内存注册表返回。

        Args:
            request: DRF 请求对象，body 参数:

            - module (str): 模块标识，可选值见 _ENUM_LABEL_REGISTRY 及 "tags"。

        Returns:
            ``labels`` 列表，每项为 {value, label}。
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
