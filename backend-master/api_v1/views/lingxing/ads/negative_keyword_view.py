"""否定关键词列表及指标聚合视图（否定投放 Tab）。

接受 ``campaign_id`` + ``profile_id`` 为必填参数，
可选日期范围、状态、匹配方式（match_type）与关键词搜索，
返回带指标的否定关键词列表、汇总行及分页信息。

关键词来自 lx_negative_keyword_info，
指标来自 lx_negative_keyword_metrics（decimal / int 类型，DB 端 Sum 聚合）。
"""
from __future__ import annotations

from typing import Any

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models.lingxing.ads.lx_negative_keyword_info import LxNegativeKeywordInfo
from api_v1.models import (
    LxAdPortfolios,
    LxCampaignInfo,
)
from api_v1.services.lingxing.ads_metrics_service import (
    build_negative_keyword_metrics_map,
    empty_negative_metrics,
)
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok
from api_v1.views.lingxing.ads._helpers import resolve_currency_icon

# 匹配方式中文映射
_MATCH_TYPE_LABEL: dict[str, str] = {
    "negativeExact": "否定精准",
    "negativePhrase": "否定词组",
}


class NegativeKeywordViewSet(viewsets.ViewSet):
    """否定关键词列表及指标聚合视图。"""

    @action(detail=False, methods=["post"], url_path="list")
    def list_negative_keywords(self, request: Request) -> Response:
        """分页获取否定关键词列表及聚合指标。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str): 必填，广告活动 ID。
            - profile_id (str): 必填，店铺 Profile ID。
            - date_start (str): 可选，起始日期 YYYY-MM-DD。
            - date_end (str): 可选，截止日期 YYYY-MM-DD。
            - state (str): 可选，状态过滤（enabled / archived）。
            - match_type (str): 可选，匹配方式（negativeExact / negativePhrase）。
            - keyword (str): 可选，按 keyword_text 模糊搜索。
            - pageNum (int): 可选，页码，默认 1。
            - pageSize (int): 可选，每页条数，默认 25。

        Returns:
            Response: 标准分页响应，含 total / list / summary / pageNum / pageSize。
        """
        data = request.data

        # 必填参数校验
        campaign_id = str(data.get("campaign_id") or "").strip()
        profile_id = str(data.get("profile_id") or "").strip()
        if not campaign_id or not profile_id:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        # 基础查询集
        qs = LxNegativeKeywordInfo.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
        ).order_by("id")

        # 全量 keyword_id：状态过滤前提取，保证指标聚合分母完整
        all_keyword_ids = list(qs.values_list("keyword_id", flat=True))

        # 可选过滤
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        match_type = str(data.get("match_type") or "").strip()
        if match_type:
            qs = qs.filter(match_type=match_type)

        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            qs = qs.filter(keyword_text__icontains=keyword)

        # 分页
        total, items, p_num, p_size = paginate_queryset(request, qs)

        # 货币符号 / 日期范围
        currency_icon = resolve_currency_icon(profile_id)
        date_start = str(data.get("date_start") or "").strip() or None
        date_end = str(data.get("date_end") or "").strip() or None

        # 父广告活动信息（单次点查）
        campaign_name = ""
        campaign_state = ""
        try:
            c_obj = LxCampaignInfo.objects.get(campaign_id=campaign_id, profile_id=profile_id)
            campaign_name = c_obj.name or ""
            campaign_state = c_obj.state or ""
        except LxCampaignInfo.DoesNotExist:
            pass

        # 广告组合名称映射
        portfolio_ids = [item.portfolio_id for item in items if item.portfolio_id]
        portfolio_map: dict[str, str] = {}
        if portfolio_ids:
            for p in LxAdPortfolios.objects.filter(portfolio_id__in=portfolio_ids):
                portfolio_map[str(p.portfolio_id)] = p.name or str(p.portfolio_id)

        # 指标聚合（DB 端 Sum，decimal / int 类型）
        metrics_map, summary = build_negative_keyword_metrics_map(
            all_keyword_ids, campaign_id, profile_id, date_start, date_end, currency_icon,
        )

        # 组装响应列表
        res_list: list[dict[str, Any]] = []
        for item in items:
            match_type_val = str(item.match_type or "")

            row: dict[str, Any] = {
                "keyword_id": item.keyword_id,
                "keyword_text": item.keyword_text or "",
                "match_type": match_type_val,
                "match_type_label": _MATCH_TYPE_LABEL.get(match_type_val, match_type_val),
                "state": item.state or "",
                "service_status": item.service_status or "",
                **{f"service_status_{k}": v for k, v in resolve_service_status(item.service_status).items()},
                "portfolio_name": (
                    portfolio_map.get(str(item.portfolio_id), "")
                    if item.portfolio_id else ""
                ),
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "adgroup_name": "",  # 否定关键词无广告组维度
                "adgroup_state": "",
                "created_at": str(item.creation_date) if item.creation_date else "",
            }
            row.update(metrics_map.get(str(item.keyword_id), empty_negative_metrics()))
            res_list.append(row)

        return drf_ok({
            "total": total,
            "list": res_list,
            "summary": summary,
            "currency_icon": currency_icon,
            "pageNum": p_num,
            "pageSize": p_size,
        })

