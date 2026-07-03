"""SP 广告活动基础数据视图（LxSpCampaign），提供查询与手动预算/状态调整。"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.ads.views._helpers import get_operator_name
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.ads.models.lx_ads_portfolio import LxAdsPortfolio
from apps.ads.models.lx_ads_profile import LxAdsProfile
from apps.ads.sp.models.lx_sp_ad import LxSpAd
from apps.ads.sp.models.lx_sp_campaign import LxSpCampaign
from apps.ads.sp.models.lx_sp_campaign_report import LxSpCampaignReport
from apps.sales.models.lx_exchange_rate import LxExchangeRate
from apps.sales.models.lx_shops import LxShops
from apps.sales.listing.models.lx_listing_data import LxListingData
from apps.sales.listing.models.lx_listing_tag import LxListingTag
from apps.ads.sp.rules.serializers.campaign_serializer import LxSpCampaignSerializer
from apps.ads.utils.ad_status import resolve_service_status
from apps.common.utils.pagination import paginate_queryset
from apps.common.utils.responses import drf_ok
from apps.ads.views._helpers import (
    BIDDING_STRATEGY_LABEL,
    CAMPAIGN_TYPE_SHORT,
    build_campaign_profile_key,
    build_campaign_profile_query,
    fmt_money,
    parse_exchange_rate,
)
from apps.ads.sp.rules.models.sp_bid_adjustment import AdjustmentStatusChoices, ExecutionStatusChoices
from apps.ads.sp.rules.models.sp_campaign_adjustment import (
    CampaignExecutionTypeChoices,
    SpCampaignAdjustment,
)

# 主题：参考数据懒加载缓存（每 20 分钟自动刷新，省 5 次 DB 往返/请求）


def _flat_parse_label(raw_label: str) -> list[str]:
    """[已废弃] 解析 LxProductInfo.label 字段。保留以兼容潜在外部引用。

    新代码已切换到 LxListingData.global_tags（JSON 数组），不再使用此函数。

    Args:
        raw_label (str): 原始值。

    Returns:
        list[str]: 扁平化后的标签字符串列表。
    """
    import json

    if not raw_label:
        return []
    s = raw_label.strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    return [t.strip() for t in s.split(",") if t.strip()]


def get_operator_name(request: Request) -> str:
    """获取当前登录用户的展示名（昵称优先，降级 username）。

    用于手动调整操作时写入 SpCampaignAdjustment.operator 字段，
    与 listing_tag_view 中的同名 helper 保持一致范式。

    Args:
        request (Request): DRF 请求对象。

    Returns:
        str: 用户昵称或 username；未认证返回 "未知用户"。
    """
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


class AdCampaignViewSet(viewsets.ViewSet):
    """AdCampaignViewSet 视图集。"""
    permission_classes = [IsAuthenticated]
    """SP 广告活动基础数据视图，提供查询与手动预算/状态调整。

    手动调整（adjust_budget / adjust_state）仅写入 SpCampaignAdjustment 调整记录表
    并同步更新 LxSpCampaign 实体表，不触发 Celery 任务；实际推送到亚马逊由
    专门的触发处调用 api/v1/ads/campaign-adjustment/run/ 接口完成。
    """

    def _serialize(self, obj: LxSpCampaign) -> dict[str, Any]:
        """数据序列化辅助方法。

        Args:
            obj (LxSpCampaign): SP 广告活动对象。

        Returns:
            dict[str, Any]: 序列化后的字典。
        """
        return LxSpCampaignSerializer(obj).data

    @action(detail=False, methods=["post"], url_path="list")
    @action(detail=False, methods=["post"], url_path="list")
    def list(self, request: Request) -> Response:
        """分页获取 SP 广告活动列表及指标详情（委托 selector）。"""
        from apps.ads.sp.selectors.campaign_list_selector import build_campaign_list_data
        result = build_campaign_list_data(request.data)
        return drf_ok(result)

    @action(detail=False, methods=["get"], url_path="detail")
    def campaign_info(self, request: Request) -> Response:
        """根据 ``campaign_id`` 与 ``profile_id`` 返回单条 SP 广告活动基础信息。

        主要供详情页面加载面包屑标题、店铺名与投放类型使用，不包含指标数据。

        Args:
            request (Request): DRF 请求对象，需携带 query param：

            - campaign_id (str): 广告活动 ID（必填）。
            - profile_id (str): 店铺 Profile ID（必填，用于鉴权隔离）。

        Returns:
            Response: 包含以下字段：

            - campaign_id (str): 广告活动 ID。
            - name (str): 广告活动名称。
            - targeting_type (str | None): 投放类型（AUTO / MANUAL）。
            - state (str): 活动状态。
            - sponsored_type (str): 广告类型（兼容前端，实际取 campaign_type）。
            - profile_name (str): 店铺/账号名称（取自 LxAdsProfile.name）。
        """
        campaign_id = request.query_params.get("campaign_id", "").strip()
        profile_id = request.query_params.get("profile_id", "").strip()

        if not campaign_id or not profile_id:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        try:
            obj = LxSpCampaign.objects.get(campaign_id=campaign_id, profile_id=profile_id)
        except LxSpCampaign.DoesNotExist:
            return drf_ok({}, msg="未找到对应的广告活动")

        profile_name = LxAdsProfile.objects.filter(
            profile_id=int(profile_id)
        ).values_list("name", flat=True).first() or ""

        return drf_ok({
            "campaign_id": obj.campaign_id,
            "name": obj.name,
            "targeting_type": obj.targeting_type or "",
            "state": obj.state,
            "sponsored_type": obj.campaign_type,
            "profile_name": profile_name,
        })

    @action(detail=False, methods=["post"], url_path="adjust-budget")
    def adjust_budget(self, request: Request) -> Response:
        """手动调整广告活动预算：写 SpCampaignAdjustment 记录 + 更新 LxSpCampaign.daily_budget。

        仅写入调整记录表与本地实体表，不触发 Celery 任务；实际推送到亚马逊由
        专门的触发处调用 api/v1/ads/campaign-adjustment/run/ 接口完成。

        Args:
            request (Request): DRF 请求对象，body 需含：
                - campaign_id (str|int): 广告活动 ID（必填）
                - profile_id (str|int): 店铺 Profile ID（必填）
                - budget_after (str|float|int): 调整后预算（必填，>0）

        Returns:
            Response: 成功返回 {campaign_id, profile_id, budget_before, budget_after}；
                      参数错误或活动不存在返回 {code, msg}。
        """
        data = request.data or {}
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        budget_after_raw = data.get("budget_after")

        if campaign_id is None or profile_id is None or budget_after_raw is None:
            return drf_ok({}, msg="campaign_id、profile_id、budget_after 均为必填参数")

        try:
            budget_after = Decimal(str(budget_after_raw))
        except (InvalidOperation, ValueError, TypeError):
            return drf_ok({}, msg="budget_after 必须为有效数值")
        if budget_after <= 0:
            return drf_ok({}, msg="budget_after 必须大于 0")

        try:
            cid_int = int(campaign_id)
            pid_int = int(profile_id)
        except (ValueError, TypeError):
            return drf_ok({}, msg="campaign_id 与 profile_id 必须为整数")

        campaign = LxSpCampaign.objects.filter(
            campaign_id=cid_int, profile_id=pid_int,
        ).only("daily_budget").first()
        if not campaign:
            return drf_ok({}, msg="未找到对应的广告活动")

        budget_before = campaign.daily_budget

        # 写调整记录表（PENDING，待专门触发处推送）
        SpCampaignAdjustment.objects.create(
            campaign_id=cid_int,
            profile_id=pid_int,
            execution_type=CampaignExecutionTypeChoices.MANUAL_BUDGET_ADJUSTMENT,
            budget_before=float(budget_before) if budget_before is not None else None,
            budget_after=float(budget_after),
            adjustment_status=AdjustmentStatusChoices.PENDING,
            execution_status=ExecutionStatusChoices.PENDING,
            adjustment_time=timezone.now(),
            operator=get_operator_name(request),
        )

        # 同步更新本地实体表预算
        LxSpCampaign.objects.filter(
            campaign_id=cid_int, profile_id=pid_int,
        ).update(daily_budget=budget_after)

        return drf_ok({
            "campaign_id": cid_int,
            "profile_id": pid_int,
            "budget_before": float(budget_before) if budget_before is not None else None,
            "budget_after": float(budget_after),
        })

    @action(detail=False, methods=["post"], url_path="adjust-state")
    def adjust_state(self, request: Request) -> Response:
        """手动调整广告活动状态：写 SpCampaignAdjustment 记录 + 更新 LxSpCampaign.state。

        state=enabled 写 CAMPAIGN_ENABLE 类型，state=paused 写 CAMPAIGN_PAUSE 类型（复用）。
        仅写入调整记录表与本地实体表，不触发 Celery 任务；实际推送到亚马逊由
        专门的触发处调用 api/v1/ads/campaign-adjustment/run/ 接口完成。

        Args:
            request (Request): DRF 请求对象，body 需含：
                - campaign_id (str|int): 广告活动 ID（必填）
                - profile_id (str|int): 店铺 Profile ID（必填）
                - state (str): 目标状态，仅支持 "enabled" / "paused"（必填）

        Returns:
            Response: 成功返回 {campaign_id, profile_id, state}；
                      参数错误或活动不存在返回 {code, msg}。
        """
        data = request.data or {}
        campaign_id = data.get("campaign_id")
        profile_id = data.get("profile_id")
        state = str(data.get("state") or "").strip().lower()

        if campaign_id is None or profile_id is None or not state:
            return drf_ok({}, msg="campaign_id、profile_id、state 均为必填参数")
        if state not in ("enabled", "paused"):
            return drf_ok({}, msg="state 仅支持 enabled / paused")

        try:
            cid_int = int(campaign_id)
            pid_int = int(profile_id)
        except (ValueError, TypeError):
            return drf_ok({}, msg="campaign_id 与 profile_id 必须为整数")

        campaign = LxSpCampaign.objects.filter(
            campaign_id=cid_int, profile_id=pid_int,
        ).only("state").first()
        if not campaign:
            return drf_ok({}, msg="未找到对应的广告活动")

        execution_type = (
            CampaignExecutionTypeChoices.CAMPAIGN_ENABLE
            if state == "enabled"
            else CampaignExecutionTypeChoices.CAMPAIGN_PAUSE
        )

        # 写调整记录表（PENDING，待专门触发处推送）
        SpCampaignAdjustment.objects.create(
            campaign_id=cid_int,
            profile_id=pid_int,
            execution_type=execution_type,
            adjustment_status=AdjustmentStatusChoices.PENDING,
            execution_status=ExecutionStatusChoices.PENDING,
            adjustment_time=timezone.now(),
            operator=get_operator_name(request),
        )

        # 同步更新本地实体表状态
        LxSpCampaign.objects.filter(
            campaign_id=cid_int, profile_id=pid_int,
        ).update(state=state)

        return drf_ok({
            "campaign_id": cid_int,
            "profile_id": pid_int,
            "state": state,
        })

    @action(detail=False, methods=["post"], url_path="batch-adjust-state")
    def batch_adjust_state(self, request: Request) -> Response:
        """批量调整广告活动状态：为每个选中活动写 SpCampaignAdjustment 记录 + 更新 LxSpCampaign.state。

        逐条校验并创建审计记录，最后统一批量更新实体状态，失败项不影响其他项。

        Args:
            request (Request): DRF 请求对象，body 需含：
                - items (list): 每项含 campaign_id + profile_id + state

        Returns:
            Response: {success_count, failed_count, errors}
        """
        data = request.data or {}
        items = data.get("items") or []
        if not items or not isinstance(items, list):
            return drf_ok({"success_count": 0, "failed_count": 0, "errors": []}, msg="items 不能为空")

        operator = get_operator_name(request)
        records: list[SpCampaignAdjustment] = []
        update_pairs: list[tuple[int, int, str]] = []
        errors: list[dict[str, Any]] = []

        for item in items:
            cid = item.get("campaign_id")
            pid = item.get("profile_id")
            state = str(item.get("state") or "").strip().lower()

            if cid is None or pid is None or state not in ("enabled", "paused"):
                errors.append({"campaign_id": cid, "message": "参数不完整或 state 无效"})
                continue

            try:
                cid_int = int(cid)
                pid_int = int(pid)
            except (ValueError, TypeError):
                errors.append({"campaign_id": cid, "message": "campaign_id / profile_id 必须为整数"})
                continue

            execution_type = (
                CampaignExecutionTypeChoices.CAMPAIGN_ENABLE
                if state == "enabled"
                else CampaignExecutionTypeChoices.CAMPAIGN_PAUSE
            )
            records.append(SpCampaignAdjustment(
                campaign_id=cid_int,
                profile_id=pid_int,
                execution_type=execution_type,
                adjustment_status=AdjustmentStatusChoices.PENDING,
                execution_status=ExecutionStatusChoices.PENDING,
                adjustment_time=timezone.now(),
                operator=operator,
            ))
            update_pairs.append((cid_int, pid_int, state))

        # 批量创建审计记录
        if records:
            SpCampaignAdjustment.objects.bulk_create(records)

        # 批量更新实体状态（按 state 分组减少 SQL 数量）
        for state_val in ("enabled", "paused"):
            pairs_for_state = [(c, p) for c, p, s in update_pairs if s == state_val]
            if pairs_for_state:
                from django.db.models import Q
                q = Q()
                for c, p in pairs_for_state:
                    q |= Q(campaign_id=c, profile_id=p)
                LxSpCampaign.objects.filter(q).update(state=state_val)

        success_count = len(update_pairs)
        return drf_ok({
            "success_count": success_count,
            "failed_count": len(errors),
            "errors": errors,
        })

    @action(detail=False, methods=["post"], url_path="batch-adjust-budget")
    def batch_adjust_budget(self, request: Request) -> Response:
        """批量调整广告活动预算：为每个选中活动写 SpCampaignAdjustment 记录 + 更新 LxSpCampaign.daily_budget。

        逐条校验并创建审计记录，最后逐条更新实体预算（因每条预算值不同），失败项不影响其他项。

        Args:
            request (Request): DRF 请求对象，body 需含：
                - items (list): 每项含 campaign_id + profile_id + budget_after

        Returns:
            Response: {success_count, failed_count, errors}
        """
        data = request.data or {}
        items = data.get("items") or []
        if not items or not isinstance(items, list):
            return drf_ok({"success_count": 0, "failed_count": 0, "errors": []}, msg="items 不能为空")

        operator = get_operator_name(request)
        records: list[SpCampaignAdjustment] = []
        update_list: list[LxSpCampaign] = []
        errors: list[dict[str, Any]] = []

        # 批量查询现有活动，避免逐条查库
        pair_list: list[tuple[int, int]] = []
        raw_map: dict[tuple[int, int], Any] = {}
        for item in items:
            cid = item.get("campaign_id")
            pid = item.get("profile_id")
            budget_raw = item.get("budget_after")
            raw_map_key = (cid, pid)
            raw_map[raw_map_key] = budget_raw
            try:
                pair_list.append((int(cid), int(pid)))
            except (ValueError, TypeError):
                continue

        existing_map: dict[tuple[int, int], LxSpCampaign] = {}
        if pair_list:
            from django.db.models import Q
            q = Q()
            for c, p in pair_list:
                q |= Q(campaign_id=c, profile_id=p)
            for obj in LxSpCampaign.objects.filter(q).only("campaign_id", "profile_id", "daily_budget"):
                existing_map[(obj.campaign_id, obj.profile_id)] = obj

        for item in items:
            cid = item.get("campaign_id")
            pid = item.get("profile_id")
            budget_raw = item.get("budget_after")

            if cid is None or pid is None or budget_raw is None:
                errors.append({"campaign_id": cid, "message": "参数不完整"})
                continue

            try:
                budget_after = Decimal(str(budget_raw))
            except (InvalidOperation, ValueError, TypeError):
                errors.append({"campaign_id": cid, "message": "budget_after 必须为有效数值"})
                continue

            if budget_after <= 0:
                errors.append({"campaign_id": cid, "message": "budget_after 必须大于 0"})
                continue

            try:
                cid_int = int(cid)
                pid_int = int(pid)
            except (ValueError, TypeError):
                errors.append({"campaign_id": cid, "message": "campaign_id / profile_id 必须为整数"})
                continue

            campaign = existing_map.get((cid_int, pid_int))
            if not campaign:
                errors.append({"campaign_id": cid, "message": "广告活动不存在"})
                continue

            budget_before = campaign.daily_budget
            records.append(SpCampaignAdjustment(
                campaign_id=cid_int,
                profile_id=pid_int,
                execution_type=CampaignExecutionTypeChoices.MANUAL_BUDGET_ADJUSTMENT,
                budget_before=float(budget_before) if budget_before is not None else None,
                budget_after=float(budget_after),
                adjustment_status=AdjustmentStatusChoices.PENDING,
                execution_status=ExecutionStatusChoices.PENDING,
                adjustment_time=timezone.now(),
                operator=operator,
            ))
            campaign.daily_budget = budget_after
            update_list.append(campaign)

        # 批量创建审计记录
        if records:
            SpCampaignAdjustment.objects.bulk_create(records)

        # 批量更新实体预算
        if update_list:
            LxSpCampaign.objects.bulk_update(update_list, ["daily_budget"])

        success_count = len(update_list)
        return drf_ok({
            "success_count": success_count,
            "failed_count": len(errors),
            "errors": errors,
        })

    @staticmethod
    def _empty_metrics() -> dict[str, Any]:
        """返回指标字段的空默认值，供无指标数据的广告活动填充占位。"""
        return {
            "adsSales": 0,
            "adsSalesPercent": 0,
            "directSales": 0,
            "adsOrders": 0,
            "directOrders": 0,
            "adsVolume": 0,
            "adsOrderPrice": 0,
            "is": "---",
            "acos": 0,
            "roas": 0,
            "cvr": 0,
            "impressions": 0,
            "impressionsPercent": 0,
            "clicks": 0,
            "clicksPercent": 0,
            "ctr": 0,
            "cpc": 0,
            "spends": 0,
            "spendsPercent": 0,
            "cpa": 0,
        }

    # 主题：最近修改信息构建
    # 查询每个广告活动 7 天内最近一次 SpCampaignAdjustment 记录，
    # 按 execution_type + auto_rule_id 是否为空区分规则/手动，构建多行展示文案。

    _ADJ_LOOKBACK_DAYS = 7

    def _build_latest_adjustment_map(
        self,
        items: list[LxSpCampaign],
        sid_to_country: dict[int, str],
        types: set | None = None,
    ) -> dict[str, dict[str, Any]]:
        """批量构建当前页每个广告活动的最近修改展示信息。

        Args:
            items (list[LxSpCampaign]): 当前页广告活动对象列表。
            sid_to_country (dict[int, str]): sid → 中文国家名映射（list 方法已构建）。
            types (set | None): 可选，限制只查这些 execution_type；None 表示全部。

        Returns:
            dict[str, dict[str, Any]]: 复合键 → {"has_recent": bool, "lines": [str]}
        """
        from datetime import timedelta
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        from apps.ads.models.lx_ads_profile import LxAdsProfile
        from apps.ads.sp.rules.models.sp_campaign_adjustment import SpCampaignAdjustment
        from apps.common.utils.timezone_utils import country_to_timezone

        # 空页直接返回
        if not items:
            return {}

        pairs = [
            (it.campaign_id, it.profile_id)
            for it in items
            if it.campaign_id and it.profile_id
        ]
        if not pairs:
            return {}

        # 7 天内最近一条调整记录
        threshold = timezone.now() - timedelta(days=self._ADJ_LOOKBACK_DAYS)
        filter_kwargs: dict[str, Any] = {
            "campaign_id__in": [c for c, _ in pairs],
            "profile_id__in": [p for _, p in pairs],
            "created_at__gte": threshold,
        }
        if types:
            filter_kwargs["execution_type__in"] = list(types)
        recent_qs = (
            SpCampaignAdjustment.objects
            .filter(**filter_kwargs)
            .order_by("-created_at")
        )
        latest_by_pair: dict[tuple[int, int], SpCampaignAdjustment] = {}
        for rec in recent_qs:
            key_pair = (rec.campaign_id, rec.profile_id)
            if key_pair not in latest_by_pair:
                latest_by_pair[key_pair] = rec

        if not latest_by_pair:
            return {}

        # 批量查规则（auto_rule_id 非空的记录）
        rule_ids = {
            r.auto_rule_id
            for r in latest_by_pair.values()
            if r.auto_rule_id
        }
        rule_map: dict[int, Any] = {}
        if rule_ids:
            from apps.ads.sp.rules.models.lx_ad_rule import LxAdRule
            for rule in LxAdRule.objects.filter(id__in=rule_ids).only(
                "id", "name", "condition_sets", "budget_action", "other_action"
            ):
                rule_map[rule.id] = rule

        # 批量查 profile 的 country_code + sid（从缓存取，省一次 DB 查询）
        profile_ids = {p for _, p in latest_by_pair.keys()}
        profile_info_map: dict[int, dict[str, str]] = {}
        if profile_ids:
            cached_profiles = get_profile_map()
            for pid in profile_ids:
                info = cached_profiles.get(str(pid))
                if info:
                    profile_info_map[pid] = {
                        "country_code": info.get("country_code", ""),
                        "sid": int(info.get("sid") or 0),
                    }

        result: dict[str, dict[str, Any]] = {}
        for (cid, pid), rec in latest_by_pair.items():
            pinfo = profile_info_map.get(pid, {})
            country_code = pinfo.get("country_code", "")
            sid = pinfo.get("sid", 0)
            country_name = sid_to_country.get(sid, country_code) or country_code or "未知"
            tz_name = country_to_timezone(country_code)
            local_time_str = self._format_local_time(rec.created_at, tz_name, country_name)

            lines = self._build_adjustment_lines(rec, rule_map, country_name, local_time_str)
            result[build_campaign_profile_key(cid, pid)] = {
                "has_recent": True,
                "lines": lines,
                "_etype": rec.execution_type,
            }
        return result

    @staticmethod
    def _format_local_time(created_at: Any, tz_name: str, country_name: str) -> str:
        """将 UTC created_at 转为站点本地时间字符串。

        Args:
            created_at: UTC datetime（Django 时区感知）。
            tz_name: 时区名，如 "Europe/Berlin"。
            country_name: 中文国家名，如 "德国"。

        Returns:
            str: "{国家名}时间: YYYY-MM-DD HH:MM"；无时区则回退原始 UTC。
        """
        from datetime import datetime
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        if not created_at:
            return f"{country_name}时间: 未知"
        try:
            if tz_name:
                tz = ZoneInfo(tz_name)
                local_dt = created_at.astimezone(tz)
            else:
                local_dt = created_at
            return f"{country_name}时间: {local_dt.strftime('%Y-%m-%d %H:%M')}"
        except (ZoneInfoNotFoundError, Exception):
            # 回退：去掉时区信息直接格式化
            try:
                return f"{country_name}时间: {created_at.strftime('%Y-%m-%d %H:%M')}"
            except Exception:
                logger.warning("[_format_local_time] 格式化时间失败: %s, %s", country_name, created_at, exc_info=True)
                return f"{country_name}时间: 未知"

    def _build_adjustment_lines(
        self,
        rec: Any,
        rule_map: dict[int, Any],
        country_name: str,
        local_time_str: str,
    ) -> list[str]:
        """根据调整记录的 execution_type + auto_rule_id 构建多行展示文案。

        四种情况：
        - 规则预算调整 / 规则启用暂停（auto_rule_id 非空）：含规则名 + 详细内容 + 执行操作。
        - 手动预算调整 / 手动启用暂停（auto_rule_id 为空）：含操作人 + 执行操作。

        Args:
            rec: SpCampaignAdjustment 实例。
            rule_map: rule_id → LxAdRule 实例映射。
            country_name: 中文国家名。
            local_time_str: 已格式化的本地时间字符串。

        Returns:
            list[str]: 多行文案，前端按 \\n 拼接展示。
        """
        from apps.ads.sp.rules.models.sp_campaign_adjustment import CampaignExecutionTypeChoices

        is_rule = bool(rec.auto_rule_id)
        rule = rule_map.get(rec.auto_rule_id) if is_rule else None
        rule_name = getattr(rule, "name", "") if rule else "未知规则"
        operator = rec.operator or "未知用户"
        etype = rec.execution_type

        # 第一行：修改来源
        if is_rule:
            line1 = f"最近一次修改通过「{rule_name}」规则修改"
        else:
            line1 = f"最近一次修改由{operator}完成"

        # 第二行：本地时间
        line2 = local_time_str

        lines = [line1, line2]

        # 预算调整类型
        if etype == CampaignExecutionTypeChoices.RULE_BUDGET_ADJUSTMENT:
            if is_rule and rule:
                lines.append(f"详细内容: {self._summarize_conditions(rule.condition_sets)}")
            lines.append(f"执行操作: {self._summarize_budget_action(rule.budget_action if rule else {}, rec)}")
        elif etype == CampaignExecutionTypeChoices.MANUAL_BUDGET_ADJUSTMENT:
            before = float(rec.budget_before) if rec.budget_before is not None else 0
            after = float(rec.budget_after) if rec.budget_after is not None else 0
            lines.append(f"执行操作: 预算 {before:.2f} → {after:.2f}")
        elif etype == CampaignExecutionTypeChoices.CAMPAIGN_PAUSE:
            if is_rule and rule:
                lines.append(f"详细内容: {self._summarize_conditions(rule.condition_sets)}")
            lines.append("执行操作: 广告活动暂停")
        elif etype == CampaignExecutionTypeChoices.CAMPAIGN_ENABLE:
            if is_rule and rule:
                lines.append(f"详细内容: {self._summarize_conditions(rule.condition_sets)}")
            lines.append("执行操作: 广告活动启用")

        return lines

    @staticmethod
    def _summarize_conditions(condition_sets: Any) -> str:
        """从 condition_sets JSON 提取所有条件组与所有条件，格式化为完整简述字符串。

        结构：condition_sets = [ {days, conditions: [{metric, operator, value, isRange?, operator2?, value2?}]}, ... ]
        组间 AND（用"；"分隔），组内条件 AND（用"，"分隔），区间模式（isRange=true）输出 "op val 且 op2 val2"。

        Args:
            condition_sets: LxAdRule.condition_sets JSON。

        Returns:
            str: 如 "近7天: 花费 > 50, 广告销售额 > 200 且 < 500；近30天: ACoS > 30"；
                  无条件返回 "无"。
        """
        # 指标字段 → 中文名映射（覆盖常见指标，与 evaluate_condition_set 的 metric_key 对齐）
        field_label = {
            "cost": "花费",
            "sales": "广告销售额",
            "same_sales": "直接销售额",
            "orders": "广告订单",
            "same_orders": "直接订单",
            "units": "广告销量",
            "clicks": "点击",
            "impressions": "曝光量",
            "ctr": "CTR",
            "cpc": "CPC",
            "cpa": "CPA",
            "acos": "ACoS",
            "roas": "ROAS",
            "cvr": "CVR",
            "spend_rate": "花费占比",
            "sales_rate": "销售额占比",
            "is_ratio": "IS",
        }
        operator_label = {
            ">": ">",
            "<": "<",
            ">=": "≥",
            "<=": "≤",
            "==": "=",
            "!=": "≠",
        }

        if not isinstance(condition_sets, list) or not condition_sets:
            return "无"

        group_parts: list[str] = []
        for cs in condition_sets:
            if not isinstance(cs, dict):
                continue
            days = cs.get("days", "?")
            conditions = cs.get("conditions") or []
            if not isinstance(conditions, list) or not conditions:
                continue
            cond_parts: list[str] = []
            for cond in conditions:
                if not isinstance(cond, dict):
                    continue
                # 字段名优先 metric（与 evaluate_condition_set 一致），回退 field
                field = str(cond.get("metric") or cond.get("field") or "")
                op = str(cond.get("operator", ">"))
                val = cond.get("value", "")
                name = field_label.get(field.lower(), field or "未知指标")
                op_sym = operator_label.get(op, op)
                seg = f"{name} {op_sym} {val}"
                # 区间模式：追加第二操作符与阈值
                if bool(cond.get("isRange", False)):
                    op2 = str(cond.get("operator2", "<"))
                    val2 = cond.get("value2", "")
                    op2_sym = operator_label.get(op2, op2)
                    seg += f" 且 {op2_sym} {val2}"
                cond_parts.append(seg)
            if cond_parts:
                group_parts.append(f"近{days}天: {', '.join(cond_parts)}")

        return "；".join(group_parts) if group_parts else "无"

    @staticmethod
    def _summarize_budget_action(budget_action: Any, rec: Any) -> str:
        """从 budget_action JSON + 记录的 before/after 构建预算操作简述。

        Args:
            budget_action: LxAdRule.budget_action JSON。
            rec: SpCampaignAdjustment 实例（含 budget_before/after）。

        Returns:
            str: 如 "预算上调 10%，上限 100"；无信息回退 before → after。
        """
        if not isinstance(budget_action, dict) or not budget_action:
            before = float(rec.budget_before) if rec.budget_before is not None else 0
            after = float(rec.budget_after) if rec.budget_after is not None else 0
            return f"预算 {before:.2f} → {after:.2f}"
        action_type = str(budget_action.get("type", ""))
        value = budget_action.get("value")
        limit = budget_action.get("limit")
        type_label = {
            "raise": "预算上调",
            "lower": "预算下调",
            "set": "预算设置为",
            "no_adjust": "预算不调整",
        }.get(action_type, "预算调整")
        parts: list[str] = []
        if value is not None:
            parts.append(f"{type_label} {value}")
        if limit is not None and limit != "":
            parts.append(f"上限 {limit}")
        return "，".join(parts) if parts else type_label

    @staticmethod
    def _compute_metrics_from_agg(
        agg_map: dict[str, dict[str, Any]],
        pairs: list[tuple[str, str]],
        *,
        total_clicks_all: int = 0,
        total_impressions_all: int = 0,
        total_spends_ref: float = 0.0,
        total_ads_sales_ref: float = 0.0,
        campaign_currency_map: dict[str, dict[str, Any]],
        is_single_currency: bool,
        rate_usd_to_cny: float = 1.0,
    ) -> dict[str, dict[str, Any]]:
        """从预聚合 agg_map 中为当前分页行计算所有衍生指标，不再访问数据库。

        Args:
            agg_map (dict): campaign 复合键 → 原始聚合值字典。
            pairs (list[tuple[str, str]]): 当前分页的 (campaign_id, profile_id) 复合键列表。
            total_clicks_all (int): 全量筛选集的点击总数。
            total_impressions_all (int): 全量筛选集的曝光总数。
            total_spends_ref (float): 全量筛选集的花费基准值（已换算为参考货币）。
            total_ads_sales_ref (float): 全量筛选集的广告销售额基准值（已换算为参考货币）。
            campaign_currency_map (dict[str, dict]): campaign 复合键 → 货币信息。
            is_single_currency (bool): 是否仅含单一货币。
            rate_usd_to_cny (float): 美元对人民币汇率。

        Returns:
            dict[str, dict[str, Any]]: campaign 复合键 → 格式化后的指标字典。
        """
        result: dict[str, dict[str, Any]] = {}
        for cid, pid in pairs:
            row_key = build_campaign_profile_key(cid, pid)
            data = agg_map.get(
                row_key,
                {"sales": 0.0, "same_sales": 0.0, "orders": 0,
                 "same_orders": 0, "units": 0, "cost": 0.0,
                 "clicks": 0, "impressions": 0},
            )
            ccy = campaign_currency_map.get(row_key, {"icon": "$", "code": "USD", "rate": rate_usd_to_cny})
            icon: str = ccy["icon"]
            rate: float = (ccy["rate"] / rate_usd_to_cny) if not is_single_currency else 1.0

            r_sales = data["sales"]
            r_same_sales = data["same_sales"]
            r_orders = data["orders"]
            r_same_orders = data["same_orders"]
            r_units = data["units"]
            r_cost = data["cost"]
            r_clicks = data["clicks"]
            r_impressions = data["impressions"]

            ref_sales = r_sales * rate
            ref_spends = r_cost * rate

            result[row_key] = {
                "adsSales": fmt_money(r_sales, icon),
                "adsSalesPercent": (
                    f"{round(ref_sales / total_ads_sales_ref * 100, 2)}%"
                    if total_ads_sales_ref > 0 else "0"
                ),
                "directSales": fmt_money(r_same_sales, icon),
                "adsOrders": r_orders,
                "directOrders": r_same_orders,
                "adsVolume": r_units,
                "adsOrderPrice": fmt_money(round(r_sales / r_orders, 2), icon) if r_orders > 0 else "0",
                "is": "---",
                "acos": f"{round(r_cost / r_sales * 100, 2)}%" if r_sales > 0 else "0",
                "roas": round(r_sales / r_cost, 2) if r_cost > 0 else 0,
                "cvr": f"{round(r_orders / r_clicks * 100, 2)}%" if r_clicks > 0 else "0",
                "impressions": r_impressions,
                "impressionsPercent": (
                    f"{round(r_impressions / total_impressions_all * 100, 2)}%"
                    if total_impressions_all > 0 else "0"
                ),
                "clicks": r_clicks,
                "clicksPercent": (
                    f"{round(r_clicks / total_clicks_all * 100, 2)}%"
                    if total_clicks_all > 0 else "0"
                ),
                "ctr": f"{round(r_clicks / r_impressions * 100, 2)}%" if r_impressions > 0 else "0",
                "cpc": fmt_money(round(r_cost / r_clicks, 2), icon) if r_clicks > 0 else "0",
                "spends": fmt_money(r_cost, icon),
                "spendsPercent": (
                    f"{round(ref_spends / total_spends_ref * 100, 2)}%"
                    if total_spends_ref > 0 else "0"
                ),
                "cpa": fmt_money(round(r_cost / r_orders, 2), icon) if r_orders > 0 else "0",
            }
        return result

    @staticmethod
    def _compute_summary_from_agg(
        agg_map: dict[str, dict[str, Any]],
        all_pairs_set: set[tuple[str, str]],
        *,
        is_single_currency: bool,
        ref_currency: dict[str, Any],
        currency_by_campaign_all: dict[str, dict[str, Any]],
        rate_usd_to_cny: float = 1.0,
        budget_by_campaign_all: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """从预聚合 agg_map 中计算汇总行与占比基准元数据，零额外数据库查询。

        Args:
            agg_map (dict): campaign 复合键 → 原始聚合值字典。
            all_pairs_set (set[tuple[str, str]]): 有效 (campaign_id, profile_id) 对集合。
            is_single_currency (bool): 是否仅含单一货币。
            ref_currency (dict): 参考货币信息。
            currency_by_campaign_all (dict): campaign → 货币信息映射（多货币时传入）。
            rate_usd_to_cny (float): 美元对人民币汇率。
            budget_by_campaign_all (dict | None): campaign 复合键 → daily_budget（本币），
                供汇总行统计预算总和，与销售额同口径换算；None 时不输出 budget 字段。

        Returns:
            dict[str, Any]: 汇总行指标字段，含 _meta 内部基准值。
        """
        icon: str = ref_currency["icon"]

        t_sales = t_same_sales = t_cost = 0.0
        t_orders = t_same_orders = t_units = t_clicks = t_impressions = 0
        t_budget = 0.0

        for cp_key, data in agg_map.items():
            key_from_map = cp_key
            try:
                parts = cp_key.split("::")
                pair = (parts[0], parts[1])
            except (IndexError, ValueError):
                continue
            if pair not in all_pairs_set:
                continue

            r_sales = data["sales"]
            r_same_sales = data["same_sales"]
            r_orders = data["orders"]
            r_same_orders = data["same_orders"]
            r_units = data["units"]
            r_cost = data["cost"]
            r_clicks = data["clicks"]
            r_impressions = data["impressions"]

            if not is_single_currency:
                ccy = currency_by_campaign_all.get(key_from_map, {"rate": rate_usd_to_cny})
                rate = ccy.get("rate", rate_usd_to_cny) / rate_usd_to_cny
                t_sales += r_sales * rate
                t_same_sales += r_same_sales * rate
                t_cost += r_cost * rate
            else:
                t_sales += r_sales
                t_same_sales += r_same_sales
                t_cost += r_cost

            t_orders += r_orders
            t_same_orders += r_same_orders
            t_units += r_units
            t_clicks += r_clicks
            t_impressions += r_impressions

        # 预算总和：按复合键从 budget_by_campaign_all 取值，多货币时换算到参考货币
        if budget_by_campaign_all is not None:
            for cp_key, raw_budget in budget_by_campaign_all.items():
                try:
                    parts = cp_key.split("::")
                    pair = (parts[0], parts[1])
                except (IndexError, ValueError):
                    continue
                if pair not in all_pairs_set:
                    continue
                if not is_single_currency:
                    ccy = currency_by_campaign_all.get(cp_key, {"rate": rate_usd_to_cny})
                    rate = ccy.get("rate", rate_usd_to_cny) / rate_usd_to_cny
                    t_budget += raw_budget * rate
                else:
                    t_budget += raw_budget

        acos = f"{round(t_cost / t_sales * 100, 2)}%" if t_sales > 0 else "0"
        roas = round(t_sales / t_cost, 2) if t_cost > 0 else 0
        cvr = f"{round(t_orders / t_clicks * 100, 2)}%" if t_clicks > 0 else "0"
        ctr = f"{round(t_clicks / t_impressions * 100, 2)}%" if t_impressions > 0 else "0"
        cpc_raw = round(t_cost / t_clicks, 2) if t_clicks > 0 else 0
        cpa_raw = round(t_cost / t_orders, 2) if t_orders > 0 else 0

        result: dict[str, Any] = {
            "adsSales": fmt_money(t_sales, icon),
            "adsSalesPercent": "100%" if t_sales > 0 else "0",
            "directSales": fmt_money(t_same_sales, icon),
            "adsOrders": t_orders,
            "directOrders": t_same_orders,
            "adsVolume": t_units,
            "adsOrderPrice": fmt_money(round(t_sales / t_orders, 2), icon) if t_orders > 0 else "0",
            "is": "---",
            "acos": acos,
            "roas": roas,
            "cvr": cvr,
            "impressions": t_impressions,
            "impressionsPercent": "100%" if t_impressions > 0 else "0",
            "clicks": t_clicks,
            "clicksPercent": "100%" if t_clicks > 0 else "0",
            "ctr": ctr,
            "cpc": fmt_money(cpc_raw, icon) if cpc_raw != 0 else "0",
            "spends": fmt_money(t_cost, icon),
            "spendsPercent": "100%" if t_cost > 0 else "0",
            "cpa": fmt_money(cpa_raw, icon) if cpa_raw != 0 else "0",
            "_meta": {
                "ads_sales_ref": round(t_sales, 6),
                "spends_ref": round(t_cost, 6),
                "clicks": t_clicks,
                "impressions": t_impressions,
            },
        }
        if budget_by_campaign_all is not None:
            result["budget"] = fmt_money(t_budget, icon)
        return result