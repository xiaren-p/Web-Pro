"""SP 投放定向条款列表及指标聚合视图（详情页 Tab：投放）。

接受 ``campaign_id`` + ``profile_id`` 为必填参数，
可选日期范围与状态筛选，返回带指标的投放条款列表、汇总行及分页信息。

自动投放条款来源于 lx_sp_target 表（expression_type=auto），
产品投放条款来源于 lx_sp_target 表（expression_type=manual），
指标来源于 lx_sp_target_report 表。
支持手动调整竞价与启停状态。
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import Sum
from django.utils import timezone
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
from api_v2.models.sp_bid_adjustment import (
    ExecutionTypeChoices as BidExecutionTypeChoices,
    SpBidAdjustment,
)
from api_v2.models.sp_bid_adjustment import AdjustmentStatusChoices, ExecutionStatusChoices


def _get_operator_name(request: Request) -> str:
    """获取当前登录用户的展示名（昵称优先，降级 username）。"""
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        try:
            profile = getattr(user, "profile", None)
            if profile and profile.nickname:
                return profile.nickname
        except Exception:
            pass
        if hasattr(user, "username") and user.username:
            return user.username
    return "未知用户"


# ── 自动投放定位组 type → 中文标签映射 ──
_AUTO_TARGETING_TYPE_MAP: dict[str, str] = {
    "queryHighRelMatches": "紧密匹配",
    "queryBroadRelMatches": "宽泛匹配",
    "asinAccessoryRelated": "同类商品",
    "asinSubstituteRelated": "关联商品",
}


def _resolve_targeting_label(expression: list[dict[str, Any]] | None) -> str:
    """将 expression JSON 数组中的 type 字段映射为中文标签。

    Args:
        expression (list[dict] | None): 表达式 JSON 数组，如 [{"type": "asinSameAs"}]。

    Returns:
        str: 中文标签，无法识别时返回 "-"。
    """
    if not expression or not isinstance(expression, list):
        return "-"
    labels = []
    for item in expression:
        if not isinstance(item, dict):
            continue
        t = item.get("type", "")
        label = _AUTO_TARGETING_TYPE_MAP.get(t)
        if label:
            labels.append(label)
    return " / ".join(labels) if labels else "-"


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
                "targeting_text": _resolve_targeting_label(item.expression),
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

        # ── 最近修改信息 ──
        adj_map = _build_bid_latest_adjustment_map(
            [str(it.target_id) for it in items if it.target_id], "target_id", pid_int,
        )
        for row in res_list:
            row["latest_adjustment"] = adj_map.get(str(row.get("target_id", "")), {"has_recent": False, "lines": []})

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

        qs = LxSpTargetReport.objects.using("analytics").filter(
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

    @action(detail=False, methods=["post"], url_path="list-product-targeting")
    def list_product_targeting(self, request: Request) -> Response:
        """分页获取商品投放条款列表及聚合指标（expression_type=manual）。

        结构镜像 list_auto_targeting，但过滤 expression_type="manual"。
        """
        data = request.data
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        if not campaign_id or not profile_id:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        date_start = data.get("date_start")
        date_end = data.get("date_end")
        state = data.get("state")
        keyword = data.get("keyword")
        p_num, p_size = self._get_page_params(data)

        qs = LxSpTarget.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
            expression_type="manual",
            state__in=["enabled", "paused"],
        ).order_by("target_id")
        if state:
            qs = qs.filter(state=state)

        total = qs.count()
        start_idx = (p_num - 1) * p_size
        end_idx = start_idx + p_size
        items = list(qs[start_idx:end_idx])

        currency_icon = self._resolve_currency_icon(int(profile_id))

        target_ids = [str(it.target_id) for it in items]
        metrics_map, summary = self._build_target_metrics(
            target_ids, int(campaign_id), int(profile_id),
            date_start, date_end, currency_icon,
        )

        ad_group_ids = {it.ad_group_id for it in items if it.ad_group_id}
        adgroup_map = {}
        campaign_map = {}
        if ad_group_ids:
            ag_qs = LxSpAdGroup.objects.filter(
                ad_group_id__in=ad_group_ids, profile_id=profile_id,
            ).values("ad_group_id", "name", "state", "campaign_id")
            for ag in ag_qs:
                adgroup_map[str(ag["ad_group_id"])] = {
                    "name": ag["name"], "state": ag["state"],
                }
                campaign_map[str(ag["ad_group_id"])] = ag["campaign_id"]

        res_list = []
        for item in items:
            row = {
                "target_id": item.target_id,
                "campaign_id": item.campaign_id,
                "profile_id": item.profile_id,
                "ad_group_id": item.ad_group_id,
                "expression": item.expression,
                "bid": float(item.bid) if item.bid is not None else None,
                "state": item.state,
                "serving_status": item.serving_status or "",
            }
            _ss = resolve_service_status(item.serving_status)
            row["service_status_label"] = _ss["label"]
            row["service_status_type"] = _ss["type"]
            ag_info = adgroup_map.get(str(item.ad_group_id), {})
            row["adgroup_name"] = ag_info.get("name", str(item.ad_group_id))
            row["adgroup_state"] = ag_info.get("state", "")
            row.update(
                metrics_map.get(str(item.target_id), empty_adgroup_metrics())
            )
            res_list.append(row)

        # ── 最近修改信息（product targeting）──
        adj_map = _build_bid_latest_adjustment_map(
            [str(it.target_id) for it in items if it.target_id], "target_id", pid_int,
        )
        for row in res_list:
            row["latest_adjustment"] = adj_map.get(str(row.get("target_id", "")), {"has_recent": False, "lines": []})

        return drf_ok({
            "total": total,
            "list": res_list,
            "summary": summary,
            "currency_icon": currency_icon,
            "pageNum": p_num,
            "pageSize": p_size,
        })

    @action(detail=False, methods=["post"], url_path="adjust-bid")
    def adjust_bid(self, request: Request) -> Response:
        """手动调整投放竞价：写 SpBidAdjustment(MANUAL_ADJUSTMENT) + 更新 LxSpTarget.bid。"""
        data = request.data or {}
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        target_id = data.get("target_id")
        bid_after_raw = data.get("bid_after")

        if campaign_id is None or profile_id is None or target_id is None or bid_after_raw is None:
            return drf_ok({}, msg="campaign_id、profile_id、target_id、bid_after 均为必填参数")
        try:
            bid_after = Decimal(str(bid_after_raw))
        except (InvalidOperation, ValueError, TypeError):
            return drf_ok({}, msg="bid_after 必须为有效数值")
        if bid_after <= 0:
            return drf_ok({}, msg="bid_after 必须大于 0")
        try:
            cid_int, pid_int, tid_int = int(campaign_id), int(profile_id), int(target_id)
        except (ValueError, TypeError):
            return drf_ok({}, msg="ID 参数必须为整数")

        tgt = LxSpTarget.objects.filter(target_id=tid_int, profile_id=pid_int).only("bid").first()
        if not tgt:
            return drf_ok({}, msg="未找到对应的投放条款")

        bid_before = tgt.bid
        SpBidAdjustment.objects.create(
            target_id=tid_int,
            campaign_id=cid_int,
            profile_id=pid_int,
            execution_type=BidExecutionTypeChoices.MANUAL_ADJUSTMENT,
            bid_before=float(bid_before) if bid_before is not None else None,
            bid_after=float(bid_after),
            adjustment_status=AdjustmentStatusChoices.PENDING,
            execution_status=ExecutionStatusChoices.PENDING,
            adjustment_time=timezone.now(),
            operator=_get_operator_name(request),
        )
        LxSpTarget.objects.filter(target_id=tid_int, profile_id=pid_int).update(bid=bid_after)

        return drf_ok({
            "target_id": tid_int,
            "campaign_id": cid_int,
            "profile_id": pid_int,
            "bid_before": float(bid_before) if bid_before is not None else None,
            "bid_after": float(bid_after),
        })

    @action(detail=False, methods=["post"], url_path="adjust-state")
    def adjust_state(self, request: Request) -> Response:
        """手动调整投放启停：写 SpBidAdjustment(BID_ENABLE/BID_PAUSE) + 更新 LxSpTarget.state。"""
        data = request.data or {}
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        target_id = data.get("target_id")
        state = str(data.get("state") or "").strip().lower()

        if campaign_id is None or profile_id is None or target_id is None or not state:
            return drf_ok({}, msg="campaign_id、profile_id、target_id、state 均为必填参数")
        if state not in ("enabled", "paused"):
            return drf_ok({}, msg="state 仅支持 enabled / paused")
        try:
            cid_int, pid_int, tid_int = int(campaign_id), int(profile_id), int(target_id)
        except (ValueError, TypeError):
            return drf_ok({}, msg="ID 参数必须为整数")

        tgt = LxSpTarget.objects.filter(target_id=tid_int, profile_id=pid_int).only("state").first()
        if not tgt:
            return drf_ok({}, msg="未找到对应的投放条款")

        execution_type = (
            BidExecutionTypeChoices.BID_ENABLE if state == "enabled"
            else BidExecutionTypeChoices.BID_PAUSE
        )
        SpBidAdjustment.objects.create(
            target_id=tid_int,
            campaign_id=cid_int,
            profile_id=pid_int,
            execution_type=execution_type,
            adjustment_status=AdjustmentStatusChoices.PENDING,
            execution_status=ExecutionStatusChoices.PENDING,
            adjustment_time=timezone.now(),
            operator=_get_operator_name(request),
        )
        LxSpTarget.objects.filter(target_id=tid_int, profile_id=pid_int).update(state=state)

        return drf_ok({
            "target_id": tid_int,
            "campaign_id": cid_int,
            "profile_id": pid_int,
            "state": state,
        })


def _build_bid_latest_adjustment_map(
    entity_ids: list[str],
    entity_field: str,
    profile_id: int,
) -> dict[str, dict[str, Any]]:
    """构建投放实体最近修改星标信息。"""
    from datetime import timedelta
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile
    from api_v1.models.lingxing.ads.lx_ad_rule import LxAdRule
    from api_v2.models.sp_bid_adjustment import SpBidAdjustment, ExecutionTypeChoices as BidExecType
    from api_v2.utils.timezone_utils import country_to_timezone

    if not entity_ids:
        return {}
    threshold = timezone.now() - timedelta(days=7)
    filter_kwargs = {
        f"{entity_field}__in": [int(x) for x in entity_ids if x],
        "created_at__gte": threshold,
    }
    recent_qs = SpBidAdjustment.objects.filter(**filter_kwargs).order_by("-created_at")
    latest_by_id: dict[int, Any] = {}
    for rec in recent_qs:
        eid = getattr(rec, entity_field, None) or rec.keyword_id or rec.target_id
        if eid is not None and eid not in latest_by_id:
            latest_by_id[eid] = rec
    if not latest_by_id:
        return {}
    rule_ids = {r.auto_rule_id for r in latest_by_id.values() if r.auto_rule_id}
    rule_map: dict[int, Any] = {}
    if rule_ids:
        for rule in LxAdRule.objects.filter(id__in=rule_ids).only("id", "name", "condition_sets"):
            rule_map[rule.id] = rule
    tz_name, country_name = "", ""
    prof = LxAdsProfile.objects.filter(profile_id=profile_id).only("country_code", "sid").first()
    if prof:
        tz_name = country_to_timezone(prof.country_code or "")
        from api_v1.models.lingxing.basic.lx_shops import LxShops
        country_name = LxShops.objects.filter(sid=prof.sid).values_list("country", flat=True).first() or (prof.country_code or "")
    result: dict[str, dict[str, Any]] = {}
    for eid, rec in latest_by_id.items():
        lines = _build_bid_lines(rec, rule_map, country_name, tz_name)
        result[str(eid)] = {"has_recent": True, "lines": lines}
    return result


def _build_bid_lines(rec: Any, rule_map: dict[int, Any], country_name: str, tz_name: str) -> list[str]:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    from api_v2.models.sp_bid_adjustment import ExecutionTypeChoices as BidExecType
    is_rule = bool(rec.auto_rule_id)
    rule = rule_map.get(rec.auto_rule_id) if is_rule else None
    rule_name = getattr(rule, "name", "") if rule else "未知规则"
    operator = rec.operator or "未知用户"
    etype = rec.execution_type
    line1 = f"最近一次修改通过「{rule_name}」规则修改" if is_rule else f"最近一次修改由{operator}完成"
    local_str = country_name + "时间: 未知"
    if rec.created_at:
        try:
            tz = ZoneInfo(tz_name) if tz_name else None
            local_dt = rec.created_at.astimezone(tz) if tz else rec.created_at
            local_str = f"{country_name or '当地'}时间: {local_dt.strftime('%Y-%m-%d %H:%M')}"
        except Exception:
            try:
                local_str = f"{country_name or '当地'}时间: {rec.created_at.strftime('%Y-%m-%d %H:%M')}"
            except Exception:
                pass
    lines = [line1, local_str]
    if is_rule and rule:
        try:
            cs = rule.condition_sets
            if isinstance(cs, list) and cs:
                fl = {"cost":"花费","sales":"广告销售额","acos":"ACoS","roas":"ROAS","clicks":"点击","impressions":"曝光量","orders":"广告订单","ctr":"CTR","cpc":"CPC","cvr":"CVR"}
                ol = {">":">","<":"<",">=":"≥","<=":"≤","==":"=","!=":"≠"}
                parts = []
                first = cs[0] if isinstance(cs[0], dict) else {}
                conds = first.get("conditions") or []
                if isinstance(conds, list):
                    for c in conds[:3]:
                        if not isinstance(c, dict): continue
                        m = str(c.get("metric") or c.get("field") or "")
                        o = str(c.get("operator", ">"))
                        v = c.get("value", "")
                        nm = fl.get(m.lower(), m or "未知")
                        osym = ol.get(o, o)
                        seg = f"{nm} {osym} {v}"
                        if bool(c.get("isRange", False)):
                            o2 = str(c.get("operator2", "<")); v2 = c.get("value2", "")
                            seg += f" 且 {ol.get(o2, o2)} {v2}"
                        parts.append(seg)
                if parts:
                    lines.append(f"详细内容: {', '.join(parts)}")
        except Exception:
            pass
    if etype == BidExecType.BID_PAUSE: lines.append("执行操作: 竞价暂停")
    elif etype == BidExecType.BID_ENABLE: lines.append("执行操作: 竞价启用")
    elif etype in (BidExecType.BID_ADJUSTMENT, BidExecType.MANUAL_ADJUSTMENT):
        bf = float(rec.bid_before) if rec.bid_before is not None else 0
        af = float(rec.bid_after) if rec.bid_after is not None else 0
        lines.append(f"执行操作: 竞价 {bf:.2f} → {af:.2f}")
    elif etype == BidExecType.TIME_PRICING_START: lines.append("执行操作: 分时开始")
    elif etype == BidExecType.TIME_PRICING_CALLBACK: lines.append("执行操作: 分时回调")
    return lines
