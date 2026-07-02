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


def _get_operator_name(request: Request) -> str:
    """获取当前登录用户的展示名（昵称优先，降级 username）。"""
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        try:
            profile = getattr(user, "profile", None)
            if profile and profile.nickname:
                return profile.nickname
        except Exception:
            logger.warning("[_get_operator_name] 获取用户昵称失败", exc_info=True)
        if hasattr(user, "username") and user.username:
            return user.username
    return "未知用户"


def _is_time_pricing_active(campaign_id: int, profile_id: int) -> bool:
    """检查指定广告活动是否正在分时生效中。

    is_time_pricing == 1(YES) 表示正在分时；0(NO) 表示分时结束。
    """
    from apps.ads.sp.timing.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus

    return AdTimePricingHit.objects.filter(
        campaign_id=campaign_id,
        profile_id=profile_id,
        is_time_pricing=TimePricingHitStatus.YES,
    ).exists()


class KeywordViewSet(viewsets.ViewSet):
    """KeywordViewSet 视图集。"""
    permission_classes = [IsAuthenticated]
    """SP 手动广告关键词列表及指标聚合视图。支持手动调整竞价与启停状态。"""

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
        currency_icon = self._resolve_currency_icon(profile_id)

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
        state_adj_map = _build_bid_latest_adjustment_map(
            keyword_ids, "keyword_id", pid,
            types={BidExecutionTypeChoices.BID_PAUSE, BidExecutionTypeChoices.BID_ENABLE},
        )
        bid_adj_map = _build_bid_latest_adjustment_map(
            keyword_ids, "keyword_id", pid,
            types={BidExecutionTypeChoices.MANUAL_ADJUSTMENT, BidExecutionTypeChoices.BID_ADJUSTMENT},
        )
        tp_adj_map = _build_bid_latest_adjustment_map(
            keyword_ids, "keyword_id", pid,
            types={BidExecutionTypeChoices.TIME_PRICING_START, BidExecutionTypeChoices.TIME_PRICING_CALLBACK},
        )
        for row in res_list:
            kid = str(row["keyword_id"])
            row["latest_state_adjustment"] = state_adj_map.get(kid, {"has_recent": False, "lines": []})
            row["latest_bid_adjustment"] = bid_adj_map.get(kid, {"has_recent": False, "lines": []})
            row["latest_time_pricing_adjustment"] = tp_adj_map.get(kid, {"has_recent": False, "lines": []})

        # 主题：分时竞价展示（仅分时生效中显示，否则 -）
        tp_bid_map = _build_time_pricing_bid_map(
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
        is_tp = _is_time_pricing_active(cid_int, pid_int)
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
            operator=_get_operator_name(request),
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
            operator=_get_operator_name(request),
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
        operator = _get_operator_name(request)

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

        is_tp = _is_time_pricing_active(cid_int, pid_int)
        operator = _get_operator_name(request)

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


def _build_bid_latest_adjustment_map(
    entity_ids: list[str],
    entity_field: str,
    profile_id: int,
    types: set | None = None,
) -> dict[str, dict[str, Any]]:
    """构建投放实体最近修改星标信息（性能优化版：用 MAX(id) 子查询取每实体最新记录）。

    Args:
        entity_ids: 实体 ID 列表。
        entity_field: "keyword_id" 或 "target_id"。
        profile_id: 店铺 Profile ID。
        types: 可选，限制只查这些 execution_type；None 表示全部。
    """
    from datetime import timedelta
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from django.db.models import Max
    from apps.ads.sp.rules.models.lx_ad_rule import LxAdRule
    from apps.ads.sp.rules.models.sp_bid_adjustment import SpBidAdjustment, ExecutionTypeChoices as BidExecType
    from apps.common.utils.timezone_utils import country_to_timezone

    if not entity_ids:
        return {}

    int_ids = [int(x) for x in entity_ids if x]
    if not int_ids:
        return {}

    threshold = timezone.now() - timedelta(days=7)
    filter_kwargs: dict[str, Any] = {
        f"{entity_field}__in": int_ids, "created_at__gte": threshold,
    }
    if types:
        filter_kwargs["execution_type__in"] = list(types)
    base_qs = SpBidAdjustment.objects.filter(
        **filter_kwargs,
    ).only("id", entity_field, "execution_type", "auto_rule_id", "operator", "bid_before", "bid_after", "created_at")

    # 用 MAX(id) GROUP BY 取每实体的最新一条记录 ID，避免全表 fetch
    latest_ids = base_qs.values(entity_field).annotate(max_id=Max("id")).values_list("max_id", flat=True)
    records = list(SpBidAdjustment.objects.filter(id__in=list(latest_ids)).only(
        "id", entity_field, "execution_type", "auto_rule_id", "operator", "bid_before", "bid_after", "created_at",
    ))

    if not records:
        return {}

    # 批量查规则
    rule_ids = {r.auto_rule_id for r in records if r.auto_rule_id}
    rule_map: dict[int, Any] = {}
    if rule_ids:
        for rule in LxAdRule.objects.filter(id__in=rule_ids).only("id", "name", "condition_sets"):
            rule_map[rule.id] = rule

    # 本地时间
    tz_name, country_name = "", ""
    prof = LxAdsProfile.objects.filter(profile_id=profile_id).only("country_code", "sid").first()
    if prof:
        tz_name = country_to_timezone(prof.country_code or "")
        from apps.sales.models.lx_shops import LxShops
        country_name = LxShops.objects.filter(sid=prof.sid).values_list("country", flat=True).first() or (prof.country_code or "")

    result: dict[str, dict[str, Any]] = {}
    for rec in records:
        eid = getattr(rec, entity_field, None) or rec.keyword_id or rec.target_id
        if eid is not None:
            lines = _build_bid_lines(rec, rule_map, country_name, tz_name)
            result[str(eid)] = {"has_recent": True, "lines": lines}
    return result


def _build_bid_lines(
    rec: Any,
    rule_map: dict[int, Any],
    country_name: str,
    tz_name: str,
) -> list[str]:
    """按 execution_type 构建多行展示文案。"""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from apps.ads.sp.rules.models.sp_bid_adjustment import ExecutionTypeChoices as BidExecType

    is_rule = bool(rec.auto_rule_id)
    rule = rule_map.get(rec.auto_rule_id) if is_rule else None
    rule_name = getattr(rule, "name", "") if rule else "未知规则"
    operator = rec.operator or "未知用户"
    etype = rec.execution_type

    # 第一行
    if is_rule:
        line1 = f"最近一次修改通过「{rule_name}」规则修改"
    else:
        line1 = f"最近一次修改由{operator}完成"

    # 第二行：本地时间
    local_time_str = country_name + "时间: 未知"
    if rec.created_at:
        try:
            if tz_name:
                tz = ZoneInfo(tz_name)
                local_dt = rec.created_at.astimezone(tz)
                local_time_str = f"{country_name or '当地'}时间: {local_dt.strftime('%Y-%m-%d %H:%M')}"
            else:
                local_time_str = f"{country_name or '当地'}时间: {rec.created_at.strftime('%Y-%m-%d %H:%M')}"
        except (ZoneInfoNotFoundError, Exception):
            logger.warning("[_build_bid_lines] 时区转换失败，降级为 UTC 时间格式", exc_info=True)
            try:
                local_time_str = f"{country_name or '当地'}时间: {rec.created_at.strftime('%Y-%m-%d %H:%M')}"
            except Exception:
                logger.warning("[_build_bid_lines] UTC 时间格式化失败", exc_info=True)

    lines = [line1, local_time_str]

    # 条件简述（规则触发时：遍历所有条件组）
    if is_rule and rule:
        try:
            cs = rule.condition_sets
            if isinstance(cs, list) and cs:
                field_label = {"cost":"花费","sales":"广告销售额","same_sales":"直接销售额","orders":"广告订单","same_orders":"直接订单","units":"广告销量","clicks":"点击","impressions":"曝光量","ctr":"CTR","cpc":"CPC","cpa":"CPA","acos":"ACoS","roas":"ROAS","cvr":"CVR","spend_rate":"花费占比","sales_rate":"销售额占比","is_ratio":"IS"}
                op_label = {">":">","<":"<",">=":"≥","<=":"≤","==":"=","!=":"≠"}
                group_parts = []
                for cg in cs:
                    if not isinstance(cg, dict): continue
                    days = cg.get("days", "?")
                    conds = cg.get("conditions") or []
                    if not isinstance(conds, list) or not conds: continue
                    cond_strs = []
                    for c in conds:
                        if not isinstance(c, dict): continue
                        m = str(c.get("metric") or c.get("field") or "")
                        o = str(c.get("operator", ">"))
                        v = c.get("value", "")
                        nm = field_label.get(m.lower(), m or "未知")
                        osym = op_label.get(o, o)
                        seg = f"{nm} {osym} {v}"
                        if bool(c.get("isRange", False)):
                            o2 = str(c.get("operator2", "<"))
                            v2 = c.get("value2", "")
                            seg += f" 且 {op_label.get(o2, o2)} {v2}"
                        cond_strs.append(seg)
                    if cond_strs:
                        group_parts.append(f"近{days}天: {', '.join(cond_strs)}")
                if group_parts:
                    lines.append(f"详细内容: {'；'.join(group_parts)}")
        except Exception:
            logger.warning("[_build_bid_lines] 规则条件解析失败", exc_info=True)

    # 执行操作
    if etype == BidExecType.BID_PAUSE:
        lines.append("执行操作: 竞价暂停")
    elif etype == BidExecType.BID_ENABLE:
        lines.append("执行操作: 竞价启用")
    elif etype in (BidExecType.BID_ADJUSTMENT, BidExecType.MANUAL_ADJUSTMENT):
        before = float(rec.bid_before) if rec.bid_before is not None else 0
        after = float(rec.bid_after) if rec.bid_after is not None else 0
        lines.append(f"执行操作: 竞价 {before:.2f} → {after:.2f}")
    elif etype == BidExecType.TIME_PRICING_START:
        lines.append("执行操作: 分时开始")
    elif etype == BidExecType.TIME_PRICING_CALLBACK:
        lines.append("执行操作: 分时回调")

    return lines


def _build_time_pricing_bid_map(
    entity_ids: list[str],
    entity_field: str,
    campaign_id: int,
    profile_id: int,
    currency_icon: str,
) -> dict[str, str]:
    """构建分时竞价展示映射：分时生效中时显示最近一次 TIME_PRICING_START 的 bid_after，否则 "-"。

    Args:
        entity_ids: 实体 ID 列表。
        entity_field: "keyword_id" 或 "target_id"。
        campaign_id: 广告活动 ID。
        profile_id: 店铺 Profile ID。
        currency_icon: 货币符号。

    Returns:
        dict[str, str]: 实体 ID → 展示字符串（如 "$0.50" 或 "-"）。
    """
    from apps.ads.sp.timing.models.ad_time_pricing_hit import AdTimePricingHit, TimePricingHitStatus

    # 未分时直接返回全 -
    if not AdTimePricingHit.objects.filter(
        campaign_id=campaign_id, profile_id=profile_id,
        is_time_pricing=TimePricingHitStatus.YES,
    ).exists():
        return {k: "-" for k in entity_ids}

    from django.db.models import Max
    from apps.ads.sp.rules.models.sp_bid_adjustment import SpBidAdjustment, ExecutionTypeChoices as BidExecType

    int_ids = [int(x) for x in entity_ids if x]
    if not int_ids:
        return {}

    # 取每个实体最近一次 TIME_PRICING_START 记录的 bid_after
    latest = (
        SpBidAdjustment.objects
        .filter(
            **{f"{entity_field}__in": int_ids},
            execution_type=BidExecType.TIME_PRICING_START,
            campaign_id=campaign_id,
            profile_id=profile_id,
        )
        .values(entity_field)
        .annotate(max_id=Max("id"))
    )
    id_map = {row[entity_field]: row["max_id"] for row in latest if row["max_id"]}
    if not id_map:
        return {k: "-" for k in entity_ids}

    records = SpBidAdjustment.objects.filter(id__in=list(id_map.values())).only(
        entity_field, "bid_after",
    )
    rec_map = {getattr(r, entity_field): r for r in records if getattr(r, entity_field)}

    result: dict[str, str] = {}
    for kid in entity_ids:
        kid_int = int(kid)
        rec = rec_map.get(kid_int)
        if rec and rec.bid_after is not None:
            result[kid] = f"{currency_icon}{float(rec.bid_after):.2f}"
        else:
            result[kid] = "-"
    return result
