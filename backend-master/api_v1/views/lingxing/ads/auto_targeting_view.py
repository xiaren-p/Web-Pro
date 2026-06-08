"""SP 自动投放定向条款列表及指标聚合视图（详情页 Tab：投放 - 自动）。

接受 ``campaign_id`` + ``profile_id`` 为必填参数，
可选日期范围与状态筛选，返回带指标的自动投放条款列表、汇总行及分页信息。

自动投放条款来源于 lx_sp_target 表（expression_type=auto），
指标来源于 lx_sp_target_report 表。
"""
from __future__ import annotations

from typing import Any

from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import (
    LxAdsPortfolio,
    LxAdsProfile,
    LxExchangeRate,
    LxSpAdGroup,
    LxSpCampaign,
    LxSpTarget,
    LxSpTargetReport,
)
from api_v1.services.lingxing.ads_metrics_service import (
    _build_summary_row,
    _compute_metrics_row,
    empty_adgroup_metrics,
)
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok


class AutoTargetingViewSet(viewsets.ViewSet):
    """SP 自动投放定向条款列表及指标聚合视图。"""

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
            return "?"
        rate = LxExchangeRate.objects.filter(
            code=profile.currency_code
        ).order_by("-date").first()
        return rate.icon if rate and rate.icon else "?"

    @action(detail=False, methods=["post"], url_path="list")
    def list_auto_targeting(self, request: Request) -> Response:
        """分页获取自动投放定向条款列表及聚合指标。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str): 必填，广告活动 ID。
            - profile_id (str): 必填，店铺 Profile ID。
            - date_start (str): 可选，起始日期 YYYY-MM-DD。
            - date_end (str): 可选，截止日期 YYYY-MM-DD。
            - state (str): 可选，状态过滤（enabled / paused / archived）。
            - pageNum (int): 可选，页码，默认 1。
            - pageSize (int): 可选，每页条数，默认 25。

        Returns:
            Response: 标准分页响应，含 ``total / list / summary / pageNum / pageSize``。
        """
        data = request.data

        # 必填参数校验与类型转换
        campaign_id_raw = data.get("campaign_id")
        profile_id_raw = data.get("profile_id")
        if not campaign_id_raw or not profile_id_raw:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        try:
            campaign_id = int(str(campaign_id_raw).strip())
            profile_id = int(str(profile_id_raw).strip())
        except (ValueError, TypeError):
            return drf_ok({}, msg="campaign_id 与 profile_id 必须为有效数字")

        # 基础查询集：仅自动投放（expression_type=auto），按 campaign_id + profile_id 隔离
        qs = LxSpTarget.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
            expression_type="auto",
        ).order_by("id")

        # 全量 target_id：必须在状态过滤前提取，保证指标汇总分母始终覆盖完整广告活动
        all_target_ids = [str(tid) for tid in qs.values_list("target_id", flat=True)]

        # 可选状态过滤（仅影响分页展示，不影响指标聚合分母）
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        # 分页
        total, items, p_num, p_size = paginate_queryset(request, qs)

        # ── 货币符号（LxAdsProfile → LxExchangeRate，一步查表）──
        currency_icon = self._resolve_currency_icon(profile_id)

        # ── 父广告活动基础信息（单次点查）──
        campaign_name = ""
        campaign_state = ""
        campaign_portfolio_name = ""
        bidding_strategy = ""
        try:
            c_obj = LxSpCampaign.objects.get(
                campaign_id=campaign_id, profile_id=profile_id
            )
            campaign_name = c_obj.name or ""
            campaign_state = c_obj.state or ""
            # portfolio_name：LxSpTarget 无 portfolio_id，通过 Campaign 间接获取
            if c_obj.portfolio_id:
                pf = LxAdsPortfolio.objects.filter(
                    portfolio_id=c_obj.portfolio_id, profile_id=profile_id
                ).first()
                campaign_portfolio_name = pf.name or str(c_obj.portfolio_id) if pf else ""
            # bidding_strategy：从 LxSpCampaign.bidding JSON 中提取 strategy 字段
            if c_obj.bidding:
                bidding_strategy = (
                    c_obj.bidding.get("strategy", "")
                    if isinstance(c_obj.bidding, dict) else ""
                )
        except LxSpCampaign.DoesNotExist:
            pass

        # ── 广告组名称批量映射 ──
        item_ad_group_ids = list({
            item.ad_group_id for item in items if item.ad_group_id
        })
        adgroup_map: dict[int, str] = {}
        adgroup_state_map: dict[int, str] = {}
        if item_ad_group_ids:
            for g in LxSpAdGroup.objects.filter(
                ad_group_id__in=item_ad_group_ids,
                campaign_id=campaign_id,
                profile_id=profile_id,
            ).values("ad_group_id", "name", "state"):
                gid = g["ad_group_id"]
                adgroup_map[gid] = g["name"] or ""
                adgroup_state_map[gid] = g["state"] or ""

        # ── 指标聚合（LxSpTargetReport + DB Sum()）──
        date_start = str(data.get("date_start") or "").strip() or None
        date_end = str(data.get("date_end") or "").strip() or None
        metrics_map, summary = self._build_target_metrics(
            all_target_ids, campaign_id, profile_id,
            date_start, date_end, currency_icon,
        )

        # ── 组装响应列表 ──
        res_list: list[dict[str, Any]] = []
        for item in items:
            gid_val = item.ad_group_id

            row: dict[str, Any] = {
                "target_id": item.target_id,
                "targeting_text": item.resolved_expression or "-",
                "state": item.state or "",
                "service_status": item.serving_status or "",
                **{
                    f"service_status_{k}": v
                    for k, v in resolve_service_status(item.serving_status).items()
                },
                "bid": float(item.bid) if item.bid is not None else "-",
                "bidding_strategy": bidding_strategy,
                "recommended_bid": "-",
                "recommend_range_start": "-",
                "recommend_range_end": "-",
                "portfolio_name": campaign_portfolio_name,
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "adgroup_name": adgroup_map.get(gid_val, "") if gid_val else "",
                "adgroup_state": adgroup_state_map.get(gid_val, "") if gid_val else "",
                "created_at": str(item.creation_date) if item.creation_date else "",
                "tag": "-",
            }
            # 合并指标数据（IS 固定为 "---"）
            row.update(
                metrics_map.get(str(item.target_id), empty_adgroup_metrics())
            )
            row["is"] = "---"
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
    def _build_target_metrics(
        target_ids: list[str],
        campaign_id: int,
        profile_id: int,
        date_start: str | None,
        date_end: str | None,
        currency_icon: str,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        """按 target_id 聚合 SP 商品定位报表指标。

        使用 DB 端 GROUP BY + Sum() 聚合（新表字段为原生数值类型 DecimalField/IntegerField）。
        无 IS 字段，所有位置固定返回 "---"。

        Args:
            target_ids (list[str]): 全量 target_id 列表（字符串形式，供 IN 查询）。
            campaign_id (int): 广告活动 ID。
            profile_id (int): 店铺 Profile ID。
            date_start (str | None): 起始日期。
            date_end (str | None): 截止日期。
            currency_icon (str): 货币符号。

        Returns:
            tuple[dict, dict]: (metrics_map, summary)。
        """
        if not target_ids:
            summary = _build_summary_row(0.0, 0.0, 0, 0, 0, 0.0, 0, 0, currency_icon)
            summary["is"] = "---"
            return {}, summary

        qs = LxSpTargetReport.objects.filter(
            target_id__in=target_ids,
            campaign_id=campaign_id,
            profile_id=profile_id,
        )
        if date_start:
            qs = qs.filter(report_date__gte=date_start)
        if date_end:
            qs = qs.filter(report_date__lte=date_end)

        agg_rows = list(
            qs.values("target_id").annotate(
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
            summary = _build_summary_row(0.0, 0.0, 0, 0, 0, 0.0, 0, 0, currency_icon)
            summary["is"] = "---"
            return {}, summary

        # 第一轮：累加全量合计
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

        # 第二轮：基于全量合计计算每行衍生指标
        metrics_map: dict[str, dict[str, Any]] = {}
        for row in agg_rows:
            row_key = str(row["target_id"])
            metrics = _compute_metrics_row(
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
            metrics["is"] = "---"
            metrics_map[row_key] = metrics

        summary = _build_summary_row(
            tot_sales, tot_same_sales, tot_orders, tot_same_orders,
            tot_units, tot_cost, tot_clicks, tot_impressions,
            currency_icon,
        )
        summary["is"] = "---"
        return metrics_map, summary
