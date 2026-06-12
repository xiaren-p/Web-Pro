"""SP 广告投放列表及指标聚合视图（详情页 Tab：投放）。

接受 ``ad_group_id`` + ``campaign_id`` + ``profile_id`` 为必填参数，
可选日期范围与筛选条件，返回带指标的广告投放列表、汇总行及分页信息。

因为 lx_ad_metrics 不含 ad_group_id 字段，视图层须先获取广告组下
全量 ad_id，再将其传入指标服务完成 IN 子句聚合查询，保证 % 分母完整。
"""
from __future__ import annotations

from typing import Any

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import (
    LxAdsPortfolio,
    LxAdsProfile,
    LxExchangeRate,
    LxListingData,
    LxSpAd,
    LxSpAdGroup,
    LxSpCampaign,
)
from api_v1.services.lingxing.ads_metrics_service import (
    build_ad_metrics_map,
    empty_adgroup_metrics,
)
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok


class AdViewSet(viewsets.ViewSet):
    """SP 广告投放列表及指标聚合视图。"""

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
        try:
            rate = LxExchangeRate.objects.filter(
                code=profile.currency_code
            ).order_by("-date").first()
        except Exception:
            return "?"
        return rate.icon if rate and rate.icon else "?"

    @action(detail=False, methods=["post"], url_path="list")
    def list_ads(self, request: Request) -> Response:
        """分页获取 SP 广告投放列表及聚合指标。

        Args:
            request (Request): DRF 请求对象，body 字段：

            - campaign_id (str): 必填，广告活动 ID。
            - profile_id (str): 必填，店铺 Profile ID。
            - ad_group_id (str): 可选，广告组 ID；不传则展示整个广告活动下的所有投放。
            - date_start (str): 可选，起始日期 YYYY-MM-DD。
            - date_end (str): 可选，截止日期 YYYY-MM-DD。
            - state (str): 可选，投放状态过滤（enabled / paused / archived）。
            - service_status (str): 可选，服务状态过滤。
            - keyword (str): 可选，ASIN 或 MSKU 模糊搜索。

        Returns:
            Response: 标准分页响应，含 ``total / list / summary / currency_icon / pageNum / pageSize``。
        """
        data = request.data

        # 必填参数校验与类型转换（新模型 campaign_id / profile_id 为 BigIntegerField）
        campaign_id_raw = data.get("campaign_id")
        profile_id_raw = data.get("profile_id")
        if not campaign_id_raw or not profile_id_raw:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        try:
            campaign_id = int(str(campaign_id_raw).strip())
            profile_id = int(str(profile_id_raw).strip())
        except (ValueError, TypeError):
            return drf_ok({}, msg="campaign_id 与 profile_id 必须为有效数字")

        # 基础查询集：按 campaign_id + profile_id 隔离
        qs = LxSpAd.objects.filter(
            campaign_id=campaign_id,
            profile_id=profile_id,
        ).order_by("ad_id")

        # 可选广告组过滤
        ad_group_id_raw = str(data.get("ad_group_id") or "").strip()
        if ad_group_id_raw:
            try:
                ad_group_id = int(ad_group_id_raw)
                qs = qs.filter(ad_group_id=ad_group_id)
            except (ValueError, TypeError):
                pass

        # 可选状态过滤
        state = str(data.get("state") or "").strip()
        if state:
            qs = qs.filter(state=state)

        # 可选服务状态过滤
        serving_status = str(data.get("service_status") or "").strip()
        if serving_status:
            qs = qs.filter(serving_status=serving_status)

        # 可选关键词过滤（ASIN 或 MSKU）
        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            qs = qs.filter(Q(asin__icontains=keyword) | Q(sku__icontains=keyword))

        # 提前获取全量 ad_id（分页前），保证 % 指标分母覆盖完整广告组
        all_ad_ids = [str(ad_id) for ad_id in qs.values_list("ad_id", flat=True)]

        # 分页
        total, items, p_num, p_size = paginate_queryset(request, qs)

        # ── 货币符号（LxAdsProfile.currency_code → LxExchangeRate.code，一步查表）──
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
            # portfolio_name：LxSpAd 无 portfolio_id，通过 LxSpCampaign 间接获取
            if c_obj.portfolio_id:
                pf = LxAdsPortfolio.objects.filter(
                    portfolio_id=c_obj.portfolio_id, profile_id=profile_id
                ).first()
                campaign_portfolio_name = pf.name or str(c_obj.portfolio_id) if pf else ""
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

        # ── 产品详情（通过 LxSpAd.sku + LxAdsProfile.sid → LxListingData 批量获取）──
        # Step 1：获取当前 profile 的 sid
        ads_profile = LxAdsProfile.objects.filter(profile_id=profile_id).first()
        sid = ads_profile.sid if ads_profile else 0

        # Step 2：收集本页所有 SKU 并与 LxListingData 做批量匹配
        item_skus = [item.sku for item in items if item.sku]
        listing_map: dict[str, dict[str, Any]] = {}
        if item_skus and sid:
            for ld in LxListingData.objects.filter(
                seller_sku__in=item_skus, sid=sid
            ).values(
                "seller_sku", "item_name", "small_image_url",
                "listing_price", "last_star", "review_num",
                "afn_fulfillable_quantity",
            ):
                listing_map[ld["seller_sku"]] = ld

        # ── 指标聚合（传入全量 ad_id，1 次 SQL GROUP BY ad_id + Python 两轮遍历）──
        date_start = str(data.get("date_start") or "").strip() or None
        date_end = str(data.get("date_end") or "").strip() or None
        metrics_map, summary = build_ad_metrics_map(
            all_ad_ids, str(campaign_id), str(profile_id),
            date_start, date_end, currency_icon,
        )

        # ── 组装响应列表 ──
        res_list: list[dict[str, Any]] = []
        for item in items:
            ld = listing_map.get(item.sku, {})

            row: dict[str, Any] = {
                "ad_id": item.ad_id,
                "asin": item.asin or "",
                "msku": item.sku or "",
                "image_url": ld.get("small_image_url") or "",
                "title": ld.get("item_name") or "",
                "price": ld.get("listing_price") or "",
                "rating": ld.get("last_star") or "",
                "reviews": ld.get("review_num") or 0,
                "stock": ld.get("afn_fulfillable_quantity") or 0,
                "state": item.state or "",
                "service_status": item.serving_status or "",
                **{
                    f"service_status_{k}": v
                    for k, v in resolve_service_status(item.serving_status).items()
                },
                "portfolio_name": campaign_portfolio_name,
                "campaign_name": campaign_name,
                "campaign_state": campaign_state,
                "adgroup_name": (
                    adgroup_map.get(item.ad_group_id, "")
                    if item.ad_group_id else ""
                ),
                "adgroup_state": (
                    adgroup_state_map.get(item.ad_group_id, "")
                    if item.ad_group_id else ""
                ),
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
