"""SP 广告组列表及指标聚合视图（详情页 Tab：广告组）。

接受 ``campaign_id`` + ``profile_id`` 为必填参数，可选日期范围与筛选条件，
返回带指标的广告组列表、汇总行以及分页信息。

指标聚合逻辑内联于视图，
复用 :mod:`api_v1.services.ads_metrics_service` 中的纯计算函数。
"""
from __future__ import annotations

from typing import Any

from django.db.models import Count, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import (
    LxAdsPortfolio,
    LxAdsProfile,
    LxExchangeRate,
    LxSpAdGroup,
    LxSpAdGroupReport,
    LxSpCampaign,
)
from api_v1.models.lingxing.ads.basic.lx_sp_ad import LxSpAd
from api_v1.services.lingxing.ads_metrics_service import (
    _build_summary_row,
    _compute_metrics_row,
    empty_adgroup_metrics,
)
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok


class AdGroupViewSet(viewsets.ViewSet):
    """SP 广告组列表及指标聚合视图。"""

    def _resolve_currency_icon(self, profile_id: int) -> str:
        """根据 profile_id 查询货币符号（一步查表）。

        查询链路：LxAdsProfile.currency_code → LxExchangeRate.code → icon。
        取最新月份的汇率记录。

        Args:
            profile_id (int): 店铺 Profile ID。

        Returns:
            str: 货币符号，查询失败返回 "$"。
        """
        profile = LxAdsProfile.objects.filter(profile_id=profile_id).first()
        if not profile or not profile.currency_code:
            return "$"
        rate = LxExchangeRate.objects.filter(
            code=profile.currency_code
        ).order_by("-date").first()
        return rate.icon if rate and rate.icon else "$"

    @action(detail=False, methods=["post"], url_path="list")
    def list_groups(self, request: Request) -> Response:
        """分页获取 SP 广告组列表及聚合指标。

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
            Response: 标准分页响应，含 ``total / list / summary / pageNum / pageSize / currency_icon``。
        """
        data = request.data

        # 必填参数校验
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        if not campaign_id or not profile_id:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        try:
            campaign_id_int = int(str(campaign_id).strip())
            profile_id_int = int(str(profile_id).strip())
        except (ValueError, TypeError):
            return drf_ok({}, msg="campaign_id 与 profile_id 必须为有效数字")

        # 基础查询集：按 campaign_id + profile_id 隔离
        qs = LxSpAdGroup.objects.filter(
            campaign_id=campaign_id_int, profile_id=profile_id_int
        ).order_by("ad_group_id")

        # 可选筛选条件
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        serving_status = str(data.get("service_status") or "").strip()
        if serving_status:
            qs = qs.filter(serving_status=serving_status)

        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            qs = qs.filter(name__icontains=keyword)

        # 分页
        total, items, p_num, p_size = paginate_queryset(request, qs)

        # ── 父广告活动基础信息（同 campaign 下所有广告组共用，单次点查）──
        campaign_name = ""
        campaign_state = ""
        campaign_portfolio_name = ""
        try:
            c_obj = LxSpCampaign.objects.get(
                campaign_id=campaign_id_int, profile_id=profile_id_int
            )
            campaign_name = c_obj.name or ""
            campaign_state = c_obj.state or ""
            # portfolio_name：LxSpAdGroup 无 portfolio_id，通过 LxSpCampaign 间接获取
            if c_obj.portfolio_id:
                pf = LxAdsPortfolio.objects.filter(
                    portfolio_id=c_obj.portfolio_id, profile_id=profile_id_int
                ).first()
                campaign_portfolio_name = pf.name if pf else str(c_obj.portfolio_id)
        except LxSpCampaign.DoesNotExist:
            pass

        # ── 货币符号（LxAdsProfile.currency_code → LxExchangeRate.code，一步查表）──
        currency_icon = self._resolve_currency_icon(profile_id_int)

        # ── 商品广告数量统计（通过 LxSpAd 按 campaign_id + ad_group_id 分组统计）──
        item_ad_group_ids = [item.ad_group_id for item in items if item.ad_group_id]
        product_counts: dict[int, int] = {}
        if item_ad_group_ids:
            product_counts = dict(
                LxSpAd.objects
                .filter(campaign_id=campaign_id_int, ad_group_id__in=item_ad_group_ids)
                .values_list("ad_group_id")
                .annotate(cnt=Count("id"))
                .values_list("ad_group_id", "cnt")
            )

        # ── 指标聚合（LxSpAdGroupReport：1 次 SQL GROUP BY + Python 两轮遍历）──
        date_start = str(data.get("date_start") or "").strip() or None
        date_end = str(data.get("date_end") or "").strip() or None
        metrics_map, summary = self._build_metrics(
            campaign_id_int, profile_id_int,
            date_start, date_end, currency_icon,
        )

        # ── 组装响应列表 ──
        res_list = []
        for item in items:
            row: dict[str, Any] = {
                "ad_group_id": item.ad_group_id,
                "name": item.name or "",
                "state": item.state or "",
                "service_status": item.serving_status or "",
                **{
                    f"service_status_{k}": v
                    for k, v in resolve_service_status(item.serving_status).items()
                },
                "portfolio_name": campaign_portfolio_name,
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "default_bid": (
                    float(item.default_bid) if item.default_bid is not None else None
                ),
                "product": product_counts.get(item.ad_group_id, 0),
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

    @staticmethod
    def _build_metrics(
        campaign_id: int,
        profile_id: int,
        date_start: str | None,
        date_end: str | None,
        currency_icon: str,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        """按 ad_group_id 聚合 SP 广告组报表指标。

        使用 "1 次 SQL GROUP BY + Python 两轮遍历" 策略：
        - GROUP BY ad_group_id 一次性获取所有聚合行。
        - 第一轮：累加全量合计（totals）作为百分比分母。
        - 第二轮：基于合计逐行调用 ``_compute_metrics_row`` 计算衍生指标。

        Args:
            campaign_id (int): 广告活动 ID。
            profile_id (int): 店铺 Profile ID。
            date_start (str | None): 起始日期 YYYY-MM-DD。
            date_end (str | None): 截止日期 YYYY-MM-DD。
            currency_icon (str): 货币符号。

        Returns:
            tuple[dict, dict]: (metrics_map, summary) 指标映射与汇总行。
        """
        qs = LxSpAdGroupReport.objects.filter(
            campaign_id=campaign_id, profile_id=profile_id
        )
        if date_start:
            qs = qs.filter(report_date__gte=date_start)
        if date_end:
            qs = qs.filter(report_date__lte=date_end)

        # 单次 GROUP BY 聚合，DB 端完成所有 SUM
        agg_rows = list(
            qs.values("ad_group_id").annotate(
                total_sales=Sum("sales"),
                total_same_sales=Sum("same_sales"),
                total_orders=Sum("orders"),
                total_same_orders=Sum("same_orders"),
                total_units=Sum("units"),
                total_cost=Sum("cost"),
                total_clicks=Sum("clicks"),
                total_impressions=Sum("impressions"),
            )
        )

        if not agg_rows:
            return {}, _build_summary_row(0.0, 0.0, 0, 0, 0, 0.0, 0, 0, currency_icon)

        # 第一轮遍历：累加全量合计，作为各 % 字段的分母基准
        tot_sales = tot_same_sales = tot_cost = 0.0
        tot_orders = tot_same_orders = tot_units = tot_clicks = tot_impressions = 0

        for row in agg_rows:
            tot_sales += float(row["total_sales"] or 0)
            tot_same_sales += float(row["total_same_sales"] or 0)
            tot_cost += float(row["total_cost"] or 0)
            tot_orders += int(row["total_orders"] or 0)
            tot_same_orders += int(row["total_same_orders"] or 0)
            tot_units += int(row["total_units"] or 0)
            tot_clicks += int(row["total_clicks"] or 0)
            tot_impressions += int(row["total_impressions"] or 0)

        # 第二轮遍历：基于全量合计计算每行衍生指标
        metrics_map: dict[str, dict[str, Any]] = {}
        for row in agg_rows:
            metrics_map[str(row["ad_group_id"])] = _compute_metrics_row(
                float(row["total_sales"] or 0),
                float(row["total_same_sales"] or 0),
                int(row["total_orders"] or 0),
                int(row["total_same_orders"] or 0),
                int(row["total_units"] or 0),
                float(row["total_cost"] or 0),
                int(row["total_clicks"] or 0),
                int(row["total_impressions"] or 0),
                currency_icon,
                tot_sales=tot_sales,
                tot_spends=tot_cost,
                tot_clicks=tot_clicks,
                tot_impressions=tot_impressions,
            )

        summary = _build_summary_row(
            tot_sales, tot_same_sales, tot_orders, tot_same_orders,
            tot_units, tot_cost, tot_clicks, tot_impressions,
            currency_icon,
        )
        return metrics_map, summary
