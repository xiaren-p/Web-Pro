"""SP 手动广告关键词列表及指标聚合视图（详情页 Tab：投放 - 关键词）。

接受 ``campaign_id`` + ``profile_id`` 为必填参数，
可选日期范围、状态、匹配方式（match_type）与关键词筛选，
返回带指标的关键词投放列表、汇总行及分页信息。
支持手动调整关键词竞价与启停状态。

关键词来源于 lx_sp_keyword 表，指标来源于 lx_sp_keyword_report 表。
结构镜像 auto_targeting_view.py，字段适配 LxSpKeyword / LxSpKeywordReport。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.ads.models.lx_ads_portfolio import LxAdsPortfolio
from apps.ads.models.lx_ads_profile import LxAdsProfile
from apps.ads.sp.models import (
LxSpAdGroup,
    LxSpCampaign,
    LxSpKeyword,
    LxSpKeywordReport,
)
from apps.sales.models.lx_exchange_rate import LxExchangeRate
from apps.sales.models.lx_shops import LxShops
from apps.sales.listing.models.lx_listing_data import LxListingData
from apps.sales.listing.models.lx_listing_tag import LxListingTag
from apps.sales.listing.models.lx_product_info import LxProductInfo
from apps.ads.sp.services.ads_metrics_service import (
    _build_summary_row,
    _compute_metrics_row,
    empty_adgroup_metrics,
)
from apps.ads.utils.ad_status import resolve_service_status
from apps.common.utils.pagination import paginate_queryset
from apps.common.utils.responses import drf_ok
from apps.ads.views._helpers import KEYWORD_MATCH_TYPE_LABEL, _sortable_val
from apps.ads.sp.rules.models.sp_bid_adjustment import (
    ExecutionTypeChoices as BidExecutionTypeChoices,
    SpBidAdjustment,
)
from apps.ads.sp.rules.models.sp_bid_adjustment import AdjustmentStatusChoices, ExecutionStatusChoices
from apps.ads.views._helpers import get_operator_name
from apps.ads.sp.selectors.currency_icon_selector import resolve_currency_icon
from apps.ads.sp.selectors.bid_adjustment_selector import build_bid_latest_adjustment_map, build_bid_lines
from apps.ads.sp.selectors.time_pricing_selector import is_time_pricing_active, build_time_pricing_bid_map


class KeywordViewSet(viewsets.ViewSet):
    """KeywordViewSet 视图集。"""
    permission_classes = [IsAuthenticated]
    """SP 手动广告关键词列表及指标聚合视图。支持手动调整竞价与启停状态。"""

    @action(detail=False, methods=["post"], url_path="list")
    def list_keywords(self, request: Request) -> Response:
        """分页获取关键词投放列表及聚合指标。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str): 必填，广告活动 ID。
            - profile_id (str): 必填，店铺 Profile ID。
            - date_start (str): 可选，起始日期 YYYY-MM-DD。
            - date_end (str): 可选，截止日期 YYYY-MM-DD。
            - state (str): 可选，状态过滤（enabled / paused / archived）。
            - match_type (str): 可选，匹配方式过滤（exact / broad / phrase）。
            - keyword (str): 可选，按 keyword_text 模糊搜索。
            - pageNum (int): 可选，页码，默认 1。
            - pageSize (int): 可选，每页条数，默认 25。

        Returns:
            Response: 标准分页响应，含 ``total / list / summary / currency_icon / pageNum / pageSize``。
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

        # 基础查询集：按 campaign_id + profile_id 隔离，按 id 排序（保持稳定分页）
        qs = LxSpKeyword.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
        ).order_by("id")

        # 全量 keyword_id：必须在状态过滤前提取，保证指标汇总分母始终覆盖完整广告活动
        all_keyword_ids = [str(kid) for kid in qs.values_list("keyword_id", flat=True)]

        # 可选状态过滤（仅影响分页展示，不影响指标聚合分母）
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        # 可选匹配方式过滤
        match_type = str(data.get("match_type") or "").strip()
        if match_type:
            qs = qs.filter(match_type=match_type)

        # 可选关键词文本模糊搜索
        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            qs = qs.filter(keyword_text__icontains=keyword)

        # 分页
        total, items, p_num, p_size = paginate_queryset(request, qs)

        # 主题：货币符号（LxAdsProfile → LxExchangeRate，一步查表）
        currency_icon = resolve_currency_icon(profile_id)

        # 主题：父广告活动基础信息（单次点查）
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
            # portfolio_name：LxSpKeyword 无 portfolio_id，通过 Campaign 间接获取
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

        # 主题：广告组名称批量映射
        item_ad_group_ids = list({
            item.ad_group_id for item in items if item.ad_group_id
        })
        adgroup_map: dict[int, str] = {}
        adgroup_state_map: dict[int, str] = {}
        adgroup_default_bid_map: dict[int, float] = {}
        if item_ad_group_ids:
            for g in LxSpAdGroup.objects.filter(
                ad_group_id__in=item_ad_group_ids,
                campaign_id=campaign_id,
                profile_id=profile_id,
            ).values("ad_group_id", "name", "state", "default_bid"):
                gid = g["ad_group_id"]
                adgroup_map[gid] = g["name"] or ""
                adgroup_state_map[gid] = g["state"] or ""
                if g.get("default_bid") is not None:
                    try:
                        adgroup_default_bid_map[gid] = float(g["default_bid"])
                    except (ValueError, TypeError):
                        pass

        # 主题：指标聚合（LxSpKeywordReport + DB Sum()）
        date_start = str(data.get("date_start") or "").strip() or None
        date_end = str(data.get("date_end") or "").strip() or None
        metrics_map, summary = self._build_metrics(
            all_keyword_ids, campaign_id, profile_id,
            date_start, date_end, currency_icon,
        )

        # 主题：组装响应列表
        res_list: list[dict[str, Any]] = []
        for item in items:
            gid_val = item.ad_group_id
            match_type_val = str(item.match_type or "")

            row: dict[str, Any] = {
                "keyword_id": item.keyword_id,
                "keyword_text": item.keyword_text or "",
                "match_type": match_type_val,
                "match_type_label": KEYWORD_MATCH_TYPE_LABEL.get(match_type_val, match_type_val),
                "bid": float(item.bid) if item.bid is not None else (adgroup_default_bid_map.get(item.ad_group_id) or "-"),
                "state": item.state or "",
                "service_status": item.serving_status or "",
                **{
                    f"service_status_{k}": v
                    for k, v in resolve_service_status(item.serving_status).items()
                },
                "bidding_strategy": bidding_strategy,
                "portfolio_name": campaign_portfolio_name,
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "adgroup_name": adgroup_map.get(gid_val, "") if gid_val else "",
                "adgroup_state": adgroup_state_map.get(gid_val, "") if gid_val else "",
                "created_at": str(item.creation_date) if item.creation_date else "",
                "tag": "-",
            }
            row.update(
                metrics_map.get(str(item.keyword_id), empty_adgroup_metrics())
            )
            res_list.append(row)

        # 主题：最近修改信息（拆分为状态变更和竞价变更两路，供两个星标各自展示）
        keyword_ids = [str(k.keyword_id) for k in items if k.keyword_id]
        pid = int(profile_id)
        state_adj_map = build_bid_latest_adjustment_map(
            keyword_ids, "keyword_id", pid,
            types={BidExecutionTypeChoices.BID_PAUSE, BidExecutionTypeChoices.BID_ENABLE},
        )
        bid_adj_map = build_bid_latest_adjustment_map(
            keyword_ids, "keyword_id", pid,
            types={BidExecutionTypeChoices.MANUAL_ADJUSTMENT, BidExecutionTypeChoices.BID_ADJUSTMENT},
        )
        tp_adj_map = build_bid_latest_adjustment_map(
            keyword_ids, "keyword_id", pid,
            types={BidExecutionTypeChoices.TIME_PRICING_START, BidExecutionTypeChoices.TIME_PRICING_CALLBACK},
        )
        for row in res_list:
            kid = str(row["keyword_id"])
            row["latest_state_adjustment"] = state_adj_map.get(kid, {"has_recent": False, "lines": []})
            row["latest_bid_adjustment"] = bid_adj_map.get(kid, {"has_recent": False, "lines": []})
            row["latest_time_pricing_adjustment"] = tp_adj_map.get(kid, {"has_recent": False, "lines": []})

        # 主题：分时竞价展示（仅分时生效中显示，否则 -）
        tp_bid_map = build_time_pricing_bid_map(
            keyword_ids, "keyword_id", int(campaign_id), int(profile_id), currency_icon,
        )
        for row in res_list:
            row["time_pricing_bid"] = tp_bid_map.get(str(row["keyword_id"]), "-")

        # 主题：排序 — 根据 sort_prop / sort_order 对 res_list 排序
        sort_prop = str(data.get("sort_prop") or "").strip()
        sort_order = str(data.get("sort_order") or "").strip()
        if sort_prop and res_list:
            reverse = sort_order == "desc"
            res_list.sort(
                key=lambda r: _sortable_val(r.get(sort_prop)),
                reverse=reverse,
            )

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
        keyword_ids: list[str],
        campaign_id: int,
        profile_id: int,
        date_start: str | None,
        date_end: str | None,
        currency_icon: str,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        """按 keyword_id 聚合 SP 关键词报表指标。

        使用 DB 端 GROUP BY + Sum() 聚合（LxSpKeywordReport 为原生数值类型）。

        Args:
            keyword_ids (list[str]): 全量 keyword_id 列表（字符串形式）。
            campaign_id (int): 广告活动 ID。
            profile_id (int): 店铺 Profile ID。
            date_start (str | None): 起始日期。
            date_end (str | None): 截止日期。
            currency_icon (str): 货币符号。

        Returns:
            tuple[dict, dict]: (metrics_map, summary)。
        """
        if not keyword_ids:
            return {}, _build_summary_row(0.0, 0.0, 0, 0, 0, 0.0, 0, 0, currency_icon)

        _cache_key = f"sp_keyword_agg:{campaign_id}|{profile_id}|{date_start or ''}|{date_end or ''}|{sorted(keyword_ids)}"
        cached = cache.get(_cache_key)
        if cached is not None:
            return cached

        qs = LxSpKeywordReport.objects.using("analytics").filter(
            keyword_id__in=keyword_ids,
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
            row_key = str(row["keyword_id"])
            metrics_map[row_key] = _compute_metrics_row(
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
        try:
            cache.set(_cache_key, (metrics_map, summary), 300)
        except Exception:
            logger.warning("[_build_metrics] 缓存写入失败", exc_info=True)
        return metrics_map, summary

    @action(detail=False, methods=["post"], url_path="adjust-bid")
    def adjust_bid(self, request: Request) -> Response:
        """手动调整关键词竞价：写 SpBidAdjustment(MANUAL_ADJUSTMENT) + 更新 LxSpKeyword.bid。"""
        data = request.data or {}
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        keyword_id = data.get("keyword_id")
        bid_after_raw = data.get("bid_after")

        if campaign_id is None or profile_id is None or keyword_id is None or bid_after_raw is None:
            return drf_ok({}, msg="campaign_id、profile_id、keyword_id、bid_after 均为必填参数")
        try:
            bid_after = Decimal(str(bid_after_raw))
        except (InvalidOperation, ValueError, TypeError):
            return drf_ok({}, msg="bid_after 必须为有效数值")
        if bid_after <= 0:
            return drf_ok({}, msg="bid_after 必须大于 0")
        try:
            cid_int, pid_int, kid_int = int(campaign_id), int(profile_id), int(keyword_id)
        except (ValueError, TypeError):
            return drf_ok({}, msg="ID 参数必须为整数")

        kw = LxSpKeyword.objects.filter(keyword_id=kid_int, profile_id=pid_int).only("bid").first()
        if not kw:
            return drf_ok({}, msg="未找到对应的关键词")

        bid_before = kw.bid
        is_tp = is_time_pricing_active(cid_int, pid_int)
        SpBidAdjustment.objects.create(
            keyword_id=kid_int,
            campaign_id=cid_int,
            profile_id=pid_int,
            execution_type=BidExecutionTypeChoices.MANUAL_ADJUSTMENT,
            bid_before=float(bid_before) if bid_before is not None else None,
            bid_after=float(bid_after),
            adjustment_status=AdjustmentStatusChoices.SUCCESS if is_tp else AdjustmentStatusChoices.PENDING,
            execution_status=ExecutionStatusChoices.SUCCESS if is_tp else ExecutionStatusChoices.PENDING,
            adjustment_time=timezone.now(),
            msg="手动修改，分时生效中，已直接应用" if is_tp else "",
            operator=get_operator_name(request),
        )
        LxSpKeyword.objects.filter(keyword_id=kid_int, profile_id=pid_int).update(bid=bid_after)

        return drf_ok({
            "keyword_id": kid_int,
            "campaign_id": cid_int,
            "profile_id": pid_int,
            "bid_before": float(bid_before) if bid_before is not None else None,
            "bid_after": float(bid_after),
        })

    @action(detail=False, methods=["post"], url_path="adjust-state")
    def adjust_state(self, request: Request) -> Response:
        """手动调整关键词启停：写 SpBidAdjustment(BID_ENABLE/BID_PAUSE) + 更新 LxSpKeyword.state。"""
        data = request.data or {}
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        keyword_id = data.get("keyword_id")
        state = str(data.get("state") or "").strip().lower()

        if campaign_id is None or profile_id is None or keyword_id is None or not state:
            return drf_ok({}, msg="campaign_id、profile_id、keyword_id、state 均为必填参数")
        if state not in ("enabled", "paused"):
            return drf_ok({}, msg="state 仅支持 enabled / paused")
        try:
            cid_int, pid_int, kid_int = int(campaign_id), int(profile_id), int(keyword_id)
        except (ValueError, TypeError):
            return drf_ok({}, msg="ID 参数必须为整数")

        kw = LxSpKeyword.objects.filter(keyword_id=kid_int, profile_id=pid_int).only("state").first()
        if not kw:
            return drf_ok({}, msg="未找到对应的关键词")

        execution_type = (
            BidExecutionTypeChoices.BID_ENABLE if state == "enabled"
            else BidExecutionTypeChoices.BID_PAUSE
        )
        SpBidAdjustment.objects.create(
            keyword_id=kid_int,
            campaign_id=cid_int,
            profile_id=pid_int,
            execution_type=execution_type,
            adjustment_status=AdjustmentStatusChoices.PENDING,
            execution_status=ExecutionStatusChoices.PENDING,
            adjustment_time=timezone.now(),
            operator=get_operator_name(request),
        )
        LxSpKeyword.objects.filter(keyword_id=kid_int, profile_id=pid_int).update(state=state)

        return drf_ok({
            "keyword_id": kid_int,
            "campaign_id": cid_int,
            "profile_id": pid_int,
            "state": state,
        })

    @action(detail=False, methods=["post"], url_path="batch-adjust-state")
    def batch_adjust_state(self, request: Request) -> Response:
        """批量调整关键词启停状态。

        逐条创建 SpBidAdjustment 审计记录，批量更新 LxSpKeyword.state。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str|int): 必填，广告活动 ID。
            - profile_id (str|int): 必填，店铺 Profile ID。
            - ids (list): 必填，关键词 ID 列表。
            - state (str): 必填，目标状态（enabled / paused）。

        Returns:
            Response: ``{success_count, failed_count, errors}``。
        """
        data = request.data or {}
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        ids = data.get("ids")
        state = str(data.get("state") or "").strip().lower()

        if not campaign_id or not profile_id or not ids or not state:
            return drf_ok({"success_count": 0, "failed_count": 0},
                          msg="campaign_id、profile_id、ids、state 均为必填参数")
        if state not in ("enabled", "paused"):
            return drf_ok({"success_count": 0, "failed_count": 0},
                          msg="state 仅支持 enabled / paused")
        try:
            cid_int, pid_int = int(campaign_id), int(profile_id)
            int_ids = [int(i) for i in ids]
        except (ValueError, TypeError):
            return drf_ok({"success_count": 0, "failed_count": 0},
                          msg="ID 参数必须为整数")

        execution_type = (
            BidExecutionTypeChoices.BID_ENABLE if state == "enabled"
            else BidExecutionTypeChoices.BID_PAUSE
        )
        operator = get_operator_name(request)

        # 批量查已存在的关键词
        existing_map = {
            kw.keyword_id: kw.state
            for kw in LxSpKeyword.objects.filter(
                keyword_id__in=int_ids, profile_id=pid_int,
            ).only("keyword_id", "state")
        }

        success_count = 0
        errors: list[dict[str, Any]] = []
        records: list[SpBidAdjustment] = []

        for kid in int_ids:
            if kid not in existing_map:
                errors.append({"id": kid, "message": "关键词不存在"})
                continue
            records.append(SpBidAdjustment(
                keyword_id=kid,
                campaign_id=cid_int,
                profile_id=pid_int,
                execution_type=execution_type,
                adjustment_status=AdjustmentStatusChoices.PENDING,
                execution_status=ExecutionStatusChoices.PENDING,
                adjustment_time=timezone.now(),
                operator=operator,
            ))
            success_count += 1

        if records:
            SpBidAdjustment.objects.bulk_create(records)
            LxSpKeyword.objects.filter(
                keyword_id__in=list(existing_map.keys()),
                profile_id=pid_int,
            ).update(state=state)

        return drf_ok({
            "success_count": success_count,
            "failed_count": len(errors),
            "errors": errors or None,
        })

    @action(detail=False, methods=["post"], url_path="batch-adjust-bid")
    def batch_adjust_bid(self, request: Request) -> Response:
        """批量调整关键词竞价。

        逐条创建 SpBidAdjustment 审计记录，批量更新 LxSpKeyword.bid。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str|int): 必填，广告活动 ID。
            - profile_id (str|int): 必填，店铺 Profile ID。
            - items (list[dict]): 必填，每项含 ``id``（keyword_id）和 ``bid``（目标竞价）。

        Returns:
            Response: ``{success_count, failed_count, errors}``。
        """
        data = request.data or {}
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        items = data.get("items")

        if not campaign_id or not profile_id or not items:
            return drf_ok({"success_count": 0, "failed_count": 0},
                          msg="campaign_id、profile_id、items 均为必填参数")
        try:
            cid_int, pid_int = int(campaign_id), int(profile_id)
        except (ValueError, TypeError):
            return drf_ok({"success_count": 0, "failed_count": 0},
                          msg="ID 参数必须为整数")

        is_tp = is_time_pricing_active(cid_int, pid_int)
        operator = get_operator_name(request)

        item_ids = [int(it["id"]) for it in items if it.get("id")]
        # 批量查已存在的关键词当前竞价
        existing_map: dict[int, LxSpKeyword] = {}
        for kw in LxSpKeyword.objects.filter(
            keyword_id__in=item_ids, profile_id=pid_int,
        ).only("id", "keyword_id", "bid"):
            existing_map[kw.keyword_id] = kw

        success_count = 0
        errors: list[dict[str, Any]] = []
        records: list[SpBidAdjustment] = []
        update_keywords: list[LxSpKeyword] = []

        for it in items:
            kid_raw = it.get("id")
            bid_raw = it.get("bid")
            if kid_raw is None or bid_raw is None:
                errors.append({"id": kid_raw, "message": "id 和 bid 均为必填"})
                continue
            try:
                kid = int(kid_raw)
                bid_after = float(bid_raw)
            except (ValueError, TypeError):
                errors.append({"id": kid_raw, "message": "id 或 bid 格式无效"})
                continue
            if bid_after <= 0:
                errors.append({"id": kid, "message": "bid 必须大于 0"})
                continue
            if kid not in existing_map:
                errors.append({"id": kid, "message": "关键词不存在"})
                continue

            kw_obj = existing_map[kid]
            bid_before = kw_obj.bid
            records.append(SpBidAdjustment(
                keyword_id=kid,
                campaign_id=cid_int,
                profile_id=pid_int,
                execution_type=BidExecutionTypeChoices.MANUAL_ADJUSTMENT,
                bid_before=float(bid_before) if bid_before is not None else None,
                bid_after=bid_after,
                adjustment_status=(
                    AdjustmentStatusChoices.SUCCESS if is_tp
                    else AdjustmentStatusChoices.PENDING
                ),
                execution_status=(
                    ExecutionStatusChoices.SUCCESS if is_tp
                    else ExecutionStatusChoices.PENDING
                ),
                adjustment_time=timezone.now(),
                msg="手动修改，分时生效中，已直接应用" if is_tp else "",
                operator=operator,
            ))
            kw_obj.bid = bid_after
            update_keywords.append(kw_obj)
            success_count += 1

        if records:
            SpBidAdjustment.objects.bulk_create(records)
            LxSpKeyword.objects.bulk_update(update_keywords, ["bid"])

        return drf_ok({
            "success_count": success_count,
            "failed_count": len(errors),
            "errors": errors or None,
        })
