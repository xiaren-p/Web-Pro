"""广告组列表及指标聚合视图（详情页 Tab：广告组）。

接受 ``campaign_id`` + ``profile_id`` 为必填参数，可选日期范围与筛选条件，
返回带指标的广告组列表、汇总行以及分页信息。

指标计算委托给 :mod:`api_v1.services.ads_metrics_service`，
视图层仅负责参数校验、DB 查询组合与响应拼装，保持单一职责。
"""
from __future__ import annotations

from typing import Any

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import (
    LxAdGroupInfo,
    LxAdGroupMetrics,
    LxAdPortfolios,
    LxCampaignInfo,
)
from api_v1.services.lingxing.ads_metrics_service import (
    build_adgroup_metrics_map,
    empty_adgroup_metrics,
)
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok
from api_v1.views.lingxing.ads._helpers import resolve_currency_icon


class AdGroupViewSet(viewsets.ViewSet):
    """广告组列表及指标聚合视图。"""

    @action(detail=False, methods=["post"], url_path="list")
    def list_groups(self, request: Request) -> Response:
        """分页获取广告组列表及聚合指标。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str): 必填，广告活动 ID。
            - profile_id (str): 必填，店铺 Profile ID。
            - date_start (str): 可选，起始日期 YYYY-MM-DD。
            - date_end (str): 可选，截止日期 YYYY-MM-DD。
            - state (str): 可选，广告组状态过滤（enabled / paused / archived）。
            - service_status (str): 可选，服务状态过滤。
            - keyword (str): 可选，广告组名称模糊搜索。

        Returns:
            Response: 标准分页响应，含 ``total / list / summary / pageNum / pageSize``。
        """
        data = request.data

        # 必填参数校验
        campaign_id = str(data.get("campaign_id") or "").strip()
        profile_id = str(data.get("profile_id") or "").strip()
        if not campaign_id or not profile_id:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        # 基础查询集：按 campaign_id + profile_id 隔离
        qs = LxAdGroupInfo.objects.filter(
            campaign_id=campaign_id, profile_id=profile_id
        ).order_by("ad_group_id")

        # 可选筛选条件
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        service_status = str(data.get("service_status") or "").strip()
        if service_status:
            qs = qs.filter(service_status=service_status)

        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            qs = qs.filter(name__icontains=keyword)

        # 分页
        total, items, p_num, p_size = paginate_queryset(request, qs)

        # 父广告活动基础信息（同 campaign 下所有广告组共用，单次点查）
        campaign_name = ""
        campaign_state = ""
        try:
            c_obj = LxCampaignInfo.objects.get(
                campaign_id=campaign_id, profile_id=profile_id
            )
            campaign_name = c_obj.name or ""
            campaign_state = c_obj.state or ""
        except LxCampaignInfo.DoesNotExist:
            pass

        # 货币符号（单一 profile → 单一国家 → 单一货币）
        currency_icon = resolve_currency_icon(profile_id)

        # 广告组合名称映射（批量查询，避免 N+1）
        portfolio_ids = [item.portfolio_id for item in items if item.portfolio_id]
        portfolio_map: dict[str, str] = {}
        if portfolio_ids:
            for p in LxAdPortfolios.objects.filter(portfolio_id__in=portfolio_ids):
                portfolio_map[str(p.portfolio_id)] = p.name or str(p.portfolio_id)

        # 指标聚合（1 次 SQL GROUP BY ad_group_id + Python 两轮遍历）
        date_start = str(data.get("date_start") or "").strip() or None
        date_end = str(data.get("date_end") or "").strip() or None
        metrics_map, summary = build_adgroup_metrics_map(
            LxAdGroupMetrics, campaign_id, profile_id,
            date_start, date_end, currency_icon,
        )

        # 组装响应列表
        res_list = []
        for item in items:
            row: dict[str, Any] = {
                "ad_group_id": item.ad_group_id,
                "name": item.name or "",
                "state": item.state or "",
                "service_status": item.service_status or "",
                **{f"service_status_{k}": v for k, v in resolve_service_status(item.service_status).items()},
                "portfolio_name": (
                    portfolio_map.get(str(item.portfolio_id), "")
                    if item.portfolio_id else ""
                ),
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "default_bid": (
                    float(item.default_bid) if item.default_bid is not None else None
                ),
                "product": item.count_product_ads or 0,
                "created_at": str(item.creation_date) if item.creation_date else "",
            }
            row.update(
                metrics_map.get(str(item.ad_group_id), empty_adgroup_metrics())
            )
            res_list.append(row)

        return drf_ok({
            "total": total,
            "list": res_list,
            "summary": summary,
            "currency_icon": currency_icon,
            "pageNum": p_num,
            "pageSize": p_size,
        })

