"""自动广告否定定向（否定商品）列表及指标聚合视图（否定投放 Tab）。

接受 ``campaign_id`` + ``profile_id`` 为必填参数，
可选日期范围、状态、否定类型（exp_type）与关键词搜索，
返回带指标的否定定向列表、汇总行及分页信息。

否定定向来自 lx_auto_negative_targeting_info，
指标来自 lx_auto_negative_targeting_metrics（VARCHAR 字段，Python 侧聚合）。
"""
from __future__ import annotations

from typing import Any

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models.ads.lx_auto_negative_targeting_info import LxAutoNegativeTargetingInfo
from api_v1.models import (
    LxAdGroupInfo,
    LxAdPortfolios,
    LxCampaignInfo,
)
from api_v1.services.ads_metrics_service import (
    build_auto_negative_targeting_metrics_map,
    empty_negative_metrics,
)
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok
from api_v1.views.ads._helpers import resolve_currency_icon

# 否定类型中文映射
_EXP_TYPE_LABEL: dict[str, str] = {
    "asin": "否定ASIN",
    "brand": "否定品牌",
}


class AutoNegativeTargetingViewSet(viewsets.ViewSet):
    """自动广告否定定向（否定商品）列表及指标聚合视图。"""

    @action(detail=False, methods=["post"], url_path="list")
    def list_auto_negative_targeting(self, request: Request) -> Response:
        """分页获取自动广告否定定向列表及聚合指标。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str): 必填，广告活动 ID。
            - profile_id (str): 必填，店铺 Profile ID。
            - date_start (str): 可选，起始日期 YYYY-MM-DD。
            - date_end (str): 可选，截止日期 YYYY-MM-DD。
            - state (str): 可选，状态过滤（enabled / archived）。
            - exp_type (str): 可选，否定类型过滤（asin / brand）。
            - keyword (str): 可选，按 exp_value 模糊搜索（ASIN 或品牌名）。
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

        # 基础查询集：按 campaign_id + profile_id 隔离
        qs = LxAutoNegativeTargetingInfo.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
        ).order_by("id")

        # 全量 target_id：状态过滤前提取，保证指标聚合分母完整
        all_target_ids = list(qs.values_list("target_id", flat=True))

        # 可选过滤
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        exp_type = str(data.get("exp_type") or "").strip()
        if exp_type:
            qs = qs.filter(exp_type=exp_type)

        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            qs = qs.filter(exp_value__icontains=keyword)

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

        # 广告组名称批量映射（避免 N+1）
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

        # 广告组合名称映射
        portfolio_ids = [item.portfolio_id for item in items if item.portfolio_id]
        portfolio_map: dict[str, str] = {}
        if portfolio_ids:
            for p in LxAdPortfolios.objects.filter(portfolio_id__in=portfolio_ids):
                portfolio_map[str(p.portfolio_id)] = p.name or str(p.portfolio_id)

        # 指标聚合（Python 侧，因 VARCHAR 字段）
        metrics_map, summary = build_auto_negative_targeting_metrics_map(
            all_target_ids, campaign_id, profile_id, date_start, date_end, currency_icon,
        )

        # 组装响应列表
        res_list: list[dict[str, Any]] = []
        for item in items:
            gid = str(item.ad_group_id) if item.ad_group_id else ""
            exp_type_val = str(item.exp_type or "")

            row: dict[str, Any] = {
                "target_id": item.target_id,
                "state": item.state or "",
                "service_status": item.service_status or "",
                **{f"service_status_{k}": v for k, v in resolve_service_status(item.service_status).items()},
                "exp_type": exp_type_val,
                "exp_type_label": _EXP_TYPE_LABEL.get(exp_type_val, exp_type_val),
                "exp_value": item.exp_value or "",
                "asin_price": item.asin_price or "-",
                "asin_stars": item.asin_stars or "-",
                "asin_review_count": item.asin_review_count or "-",
                "asin_title": item.asin_title or "",
                "portfolio_name": (
                    portfolio_map.get(str(item.portfolio_id), "")
                    if item.portfolio_id else ""
                ),
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "adgroup_name": adgroup_map.get(gid, "") if gid else "",
                "adgroup_state": adgroup_state_map.get(gid, "") if gid else "",
                "created_at": str(item.created_at) if item.created_at else "",
            }
            row.update(metrics_map.get(str(item.target_id), empty_negative_metrics()))
            res_list.append(row)

        return drf_ok({
            "total": total,
            "list": res_list,
            "summary": summary,
            "currency_icon": currency_icon,
            "pageNum": p_num,
            "pageSize": p_size,
        })
