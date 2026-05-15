"""广告投放列表及指标聚合视图（详情页 Tab：投放）。

接受 ``ad_group_id`` + ``campaign_id`` + ``profile_id`` 为必填参数，
可选日期范围与筛选条件，返回带指标的广告投放列表、汇总行及分页信息。

由于 lx_ad_metrics 不含 ad_group_id 字段，视图层须先获取广告组下
全量 ad_id，再将其传入指标服务完成 IN 子句聚合查询，保证 % 分母完整。
"""
from __future__ import annotations

from typing import Any

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import (
    LxAdGroupInfo,
    LxAdInfo,
    LxAdPortfolios,
    LxCampaignInfo,
)
from api_v1.services.ads_metrics_service import (
    build_ad_metrics_map,
    empty_adgroup_metrics,
)
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok
from api_v1.views.ads._helpers import resolve_currency_icon


class AdViewSet(viewsets.ViewSet):
    """广告投放列表及指标聚合视图。"""

    @action(detail=False, methods=["post"], url_path="list")
    def list_ads(self, request: Request) -> Response:
        """分页获取广告投放列表及聚合指标。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str): 必填，广告活动 ID。
            - profile_id (str): 必填，店铺 Profile ID。
            - ad_group_id (str): 可选，广告组 ID；不传则展示整个广告活动下的所有投放。
            - date_start (str): 可选，起始日期 YYYY-MM-DD。
            - date_end (str): 可选，截止日期 YYYY-MM-DD。
            - state (str): 可选，投放状态过滤（enabled / paused / archived）。            - service_status (str): 可选，服务状态过滤（如 AD_STATUS_LIVE / AD_PAUSED 等）。            - keyword (str): 可选，ASIN 或 MSKU 模糊搜索。

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
        qs = LxAdInfo.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
        ).order_by("ad_id")

        # 可选广告组过滤
        ad_group_id = str(data.get("ad_group_id") or "").strip()
        if ad_group_id:
            qs = qs.filter(ad_group_id=ad_group_id)

        # 可选状态过滤
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        # 可选服务状态过滤
        service_status = str(data.get("service_status") or "").strip()
        if service_status:
            qs = qs.filter(service_status=service_status)

        # 可选关键词过滤（ASIN 或 MSKU）
        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            qs = qs.filter(asin__icontains=keyword) | qs.filter(sku__icontains=keyword)

        # 提前获取全量 ad_id（分页前），保证 % 指标分母覆盖完整广告组
        all_ad_ids = list(qs.values_list("ad_id", flat=True))

        # 分页
        total, items, p_num, p_size = paginate_queryset(request, qs)

        # 货币符号
        currency_icon = resolve_currency_icon(profile_id)

        # 日期范围
        date_start = str(data.get("date_start") or "").strip() or None
        date_end = str(data.get("date_end") or "").strip() or None

        # 父广告活动基础信息（单次点查）
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

        # 广告组名称批量映射（用每条 ad 的 ad_group_id + campaign_id + profile_id 查询，
        # 避免仅按传入 ad_group_id 过滤时其他组的广告显示空名称）
        item_ad_group_ids = list({
            str(item.ad_group_id) for item in items if item.ad_group_id
        })
        adgroup_map: dict[str, str] = {}
        adgroup_state_map: dict[str, str] = {}
        if item_ad_group_ids:
            for g in LxAdGroupInfo.objects.filter(
                ad_group_id__in=item_ad_group_ids,
                campaign_id=campaign_id,
                profile_id=profile_id,
            ).values("ad_group_id", "name", "state"):
                gid = str(g["ad_group_id"])
                adgroup_map[gid] = g["name"] or ""
                adgroup_state_map[gid] = g["state"] or ""

        # 广告组合名称映射（批量查询，避免 N+1）
        portfolio_ids = [item.portfolio_id for item in items if item.portfolio_id]
        portfolio_map: dict[str, str] = {}
        if portfolio_ids:
            for p in LxAdPortfolios.objects.filter(portfolio_id__in=portfolio_ids):
                portfolio_map[str(p.portfolio_id)] = p.name or str(p.portfolio_id)

        # 指标聚合（传入全量 ad_id，1 次 SQL GROUP BY ad_id + Python 两轮遍历）
        metrics_map, summary = build_ad_metrics_map(
            all_ad_ids, campaign_id, profile_id,
            date_start, date_end, currency_icon,
        )

        # 组装响应列表
        res_list: list[dict[str, Any]] = []
        for item in items:
            row: dict[str, Any] = {
                "ad_id": item.ad_id,
                "asin": item.asin or "",
                "msku": item.sku or "",
                "image_url": item.main_img or "",
                "title": item.product_name or "",
                "price": item.listing_price or "",
                "rating": item.stars or "",
                "reviews": item.review_count or "",
                "stock": item.afn_fulfillable_quantity or 0,
                "state": item.state or "",
                "service_status": item.service_status or "",
                **{f"service_status_{k}": v for k, v in resolve_service_status(item.service_status).items()},
                "portfolio_name": (
                    portfolio_map.get(str(item.portfolio_id), "")
                    if item.portfolio_id else ""
                ),
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "adgroup_name": adgroup_map.get(str(item.ad_group_id), "") if item.ad_group_id else "",
                "adgroup_state": adgroup_state_map.get(str(item.ad_group_id), "") if item.ad_group_id else "",
                "created_at": str(item.creation_date) if item.creation_date else "",
            }
            row.update(
                metrics_map.get(str(item.ad_id), empty_adgroup_metrics())
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
