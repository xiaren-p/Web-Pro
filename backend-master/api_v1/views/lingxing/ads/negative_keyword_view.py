"""SP 否定关键词列表及指标聚合视图（否定投放 Tab）。

接受 ``campaign_id`` + ``profile_id`` 为必填参数，
可选日期范围、状态、匹配方式（negative_match_type）与关键词搜索，
返回带指标的否定关键词列表、汇总行及分页信息。

关键词来自 lx_sp_negative_target（negative_type=negativeKeyword），
指标来自 lx_sp_keyword_report（decimal / int 类型，DB 端 Sum 聚合）。
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
    LxSpCampaign,
    LxSpKeywordReport,
    LxSpNegativeTarget,
)
from api_v1.services.lingxing.ads_metrics_service import (
    _build_negative_summary_row,
    _compute_negative_row,
    empty_negative_metrics,
)
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok
from api_v1.views.lingxing.ads._helpers import NEGATIVE_MATCH_TYPE_LABEL


class NegativeKeywordViewSet(viewsets.ViewSet):
    """SP 否定关键词列表及指标聚合视图。"""

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
            - keyword (str): 可选，按关键词文本模糊搜索。
            - pageNum (int): 可选，页码，默认 1。
            - pageSize (int): 可选，每页条数，默认 25。

        Returns:
            Response: 标准分页响应，含 total / list / summary / pageNum / pageSize。
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

        # 基础查询集：仅否定关键词类型，按 campaign_id + profile_id 隔离
        qs = LxSpNegativeTarget.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
            negative_type="negativeKeyword",
        ).order_by("id")

        # 全量 target_id：状态过滤前提取，保证指标聚合分母完整
        all_target_ids = [str(tid) for tid in qs.values_list("target_id", flat=True)]

        # 可选过滤
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        match_type = str(data.get("match_type") or "").strip()
        if match_type:
            qs = qs.filter(negative_match_type=match_type)

        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            qs = qs.filter(negative_text__icontains=keyword)

        # 分页
        total, items, p_num, p_size = paginate_queryset(request, qs)

        # ── 货币符号（LxAdsProfile → LxExchangeRate，一步查表）──
        currency_icon = self._resolve_currency_icon(profile_id)

        # ── 父广告活动基础信息（单次点查）──
        campaign_name = ""
        campaign_state = ""
        campaign_portfolio_name = ""
        try:
            c_obj = LxSpCampaign.objects.get(
                campaign_id=campaign_id, profile_id=profile_id
            )
            campaign_name = c_obj.name or ""
            campaign_state = c_obj.state or ""
            # portfolio_name：LxSpNegativeTarget 无 portfolio_id，通过 Campaign 间接获取
            if c_obj.portfolio_id:
                pf = LxAdsPortfolio.objects.filter(
                    portfolio_id=c_obj.portfolio_id, profile_id=profile_id
                ).first()
                campaign_portfolio_name = pf.name or str(c_obj.portfolio_id) if pf else ""
        except LxSpCampaign.DoesNotExist:
            pass

        # ── 指标聚合（LxSpKeywordReport + DB Sum()）──
        date_start = str(data.get("date_start") or "").strip() or None
        date_end = str(data.get("date_end") or "").strip() or None
        metrics_map, summary = self._build_keyword_metrics(
            all_target_ids, campaign_id, profile_id,
            date_start, date_end, currency_icon,
        )

        # ── 组装响应列表 ──
        res_list: list[dict[str, Any]] = []
        for item in items:
            match_type_val = str(item.negative_match_type or "")

            row: dict[str, Any] = {
                "keyword_id": item.target_id,
                "keyword_text": item.negative_text or "",
                "match_type": match_type_val,
                "match_type_label": NEGATIVE_MATCH_TYPE_LABEL.get(match_type_val, match_type_val),
                "state": item.state or "",
                "service_status": item.serving_status or "",
                **{
                    f"service_status_{k}": v
                    for k, v in resolve_service_status(item.serving_status).items()
                },
                "portfolio_name": campaign_portfolio_name,
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "adgroup_name": "",
                "adgroup_state": "",
                "created_at": str(item.creation_date) if item.creation_date else "",
            }
            row.update(
                metrics_map.get(str(item.target_id), empty_negative_metrics())
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
    def _build_keyword_metrics(
        target_ids: list[str],
        campaign_id: int,
        profile_id: int,
        date_start: str | None,
        date_end: str | None,
        currency_icon: str,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        """按 target_id 聚合 SP 关键词报表指标。

        使用 DB 端 GROUP BY + Sum() 聚合（LxSpKeywordReport 字段为原生数值类型），
        匹配规则：target_id → LxSpKeywordReport.keyword_id。

        Args:
            target_ids (list[str]): 全量 target_id 列表。
            campaign_id (int): 广告活动 ID。
            profile_id (int): 店铺 Profile ID。
            date_start (str | None): 起始日期。
            date_end (str | None): 截止日期。
            currency_icon (str): 货币符号。

        Returns:
            tuple[dict, dict]: (metrics_map, summary)。
        """
        if not target_ids:
            return {}, _build_negative_summary_row(0.0, 0, 0.0, currency_icon)

        qs = LxSpKeywordReport.objects.filter(
            keyword_id__in=target_ids,
            campaign_id=campaign_id,
            profile_id=profile_id,
        )
        if date_start:
            qs = qs.filter(report_date__gte=date_start)
        if date_end:
            qs = qs.filter(report_date__lte=date_end)

        agg_rows = list(
            qs.values("keyword_id").annotate(
                total_sales=Sum("sales"),
                total_orders=Sum("orders"),
                total_cost=Sum("cost"),
            )
        )

        if not agg_rows:
            return {}, _build_negative_summary_row(0.0, 0, 0.0, currency_icon)

        # 全量合计
        tot_sales = tot_cost = 0.0
        tot_orders = 0
        for row in agg_rows:
            tot_sales += float(row["total_sales"] or 0)
            tot_cost += float(row["total_cost"] or 0)
            tot_orders += int(row["total_orders"] or 0)

        metrics_map: dict[str, dict[str, Any]] = {
            str(row["keyword_id"]): _compute_negative_row(
                float(row["total_sales"] or 0),
                int(row["total_orders"] or 0),
                float(row["total_cost"] or 0),
                currency_icon,
            )
            for row in agg_rows
        }
        summary = _build_negative_summary_row(tot_sales, tot_orders, tot_cost, currency_icon)
        return metrics_map, summary
