"""SP 广告活动基础数据视图（LxSpCampaign），仅提供查询。"""
from __future__ import annotations

from typing import Any

from django.db.models import Q, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import (
    LxAdsPortfolio,
    LxAdsProfile,
    LxExchangeRate,
    LxSpCampaign,
    LxSpCampaignReport,
)
from api_v1.serializers.lingxing.ads import LxSpCampaignSerializer
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok
from api_v1.views.lingxing.ads._helpers import (
    COUNTRY_MAP,
    build_campaign_profile_key,
    build_campaign_profile_query,
    fmt_money,
    parse_exchange_rate,
)


class AdCampaignViewSet(viewsets.ViewSet):
    """SP 广告活动基础数据视图（只提供查询）。"""

    def _serialize(self, obj: LxSpCampaign) -> dict[str, Any]:
        """数据序列化辅助方法。

        Args:
            obj (LxSpCampaign): SP 广告活动对象。

        Returns:
            dict[str, Any]: 序列化后的字典。
        """
        return LxSpCampaignSerializer(obj).data

    @action(detail=False, methods=["post"], url_path="list")
    def list(self, request: Request) -> Response:
        """分页获取 SP 广告活动列表及指标详情。

        接受复合的检索参数并在底层合并广告表及其归属的国家和店铺数据。

        Args:
            request (Request): DRF 原始请求对象。

        Returns:
            Response: 组合映射好 ``profile_alias`` 等补充数据的标准分页结果集。
        """
        qs = LxSpCampaign.objects.all().order_by("-start_date")

        data = request.data

        # ── 关键词搜索 ──
        keyword = data.get("keyword") or data.get("name")
        if isinstance(keyword, str) and keyword.strip():
            kw = keyword.strip()
            base_q = Q(name__icontains=kw)
            # campaign_id 为 BigIntegerField，不支持 icontains，仅做精确数值匹配
            try:
                base_q |= Q(campaign_id=int(kw))
            except (ValueError, TypeError):
                pass
            # 通过 LxAdsProfile.sid 反向查找匹配的 profile_id（替代旧 store_id__icontains）
            matched_pids = list(
                LxAdsProfile.objects.filter(sid__icontains=kw).values_list("profile_id", flat=True)
            )
            if matched_pids:
                base_q |= Q(profile_id__in=matched_pids)
            qs = qs.filter(base_q)

        state = data.get("state")
        if state:
            qs = qs.filter(state__in=state.split(","))

        serving_status = data.get("service_status")
        if serving_status:
            qs = qs.filter(serving_status__in=serving_status.split(","))

        campaign_type = data.get("sponsored_type")
        if campaign_type:
            qs = qs.filter(campaign_type__in=campaign_type.split(","))

        bidding_strategy = data.get("bidding_type")
        if bidding_strategy:
            # bidding 为 JSONField，内部结构为 {"strategy": "manual", "adjustments": []}
            qs = qs.filter(bidding__strategy__in=bidding_strategy.split(","))

        portfolio_id = data.get("portfolio_id")
        if portfolio_id:
            p_ids = [p for p in portfolio_id.split(",") if p]
            if "-1" in p_ids:
                p_ids.remove("-1")
                if p_ids:
                    qs = qs.filter(Q(portfolio_id__in=p_ids) | Q(portfolio_id__isnull=True))
                else:
                    qs = qs.filter(portfolio_id__isnull=True)
            else:
                qs = qs.filter(portfolio_id__in=p_ids)

        profiles = data.get("profiles")
        if profiles:
            qs = qs.filter(profile_id__in=profiles.split(","))

        countries = data.get("countries")
        if countries:
            profile_ids = LxAdsProfile.objects.filter(
                country_code__in=countries.split(",")
            ).values_list("profile_id", flat=True)
            qs = qs.filter(profile_id__in=profile_ids)

        sort_prop = data.get("sort_prop")
        sort_order = data.get("sort_order")
        if sort_prop and sort_order in ["asc", "desc"]:
            field_map = {
                "startDate": "start_date",
            }
            db_field = field_map.get(sort_prop, sort_prop)
            order_prefix = "-" if sort_order == "desc" else ""
            try:
                qs = qs.order_by(f"{order_prefix}{db_field}")
            except Exception:
                pass

        total, items, p_num, p_size = paginate_queryset(request, qs)

        # ── 组装店铺与国家数据 ──
        item_profile_ids = [item.profile_id for item in items if item.profile_id]
        profiles_page = list(LxAdsProfile.objects.filter(profile_id__in=item_profile_ids))

        profile_map: dict[str, dict[str, str]] = {}
        for sp in profiles_page:
            country = sp.country_code or ""
            c_name = COUNTRY_MAP.get(country.upper(), country)
            profile_map[str(sp.profile_id)] = {
                "profile_alias": sp.name if sp.name else str(sp.profile_id),
                "country_name": c_name,
                "sid": sp.sid or "",
            }

        # ── 组装广告组合数据（需同时匹配 portfolio_id + profile_id）──
        portfolio_pairs = [
            (item.portfolio_id, item.profile_id)
            for item in items
            if item.portfolio_id and item.profile_id
        ]
        portfolio_map: dict[str, str] = {}
        if portfolio_pairs:
            pf_q = Q()
            for pid, pfid in portfolio_pairs:
                pf_q |= Q(portfolio_id=pid, profile_id=pfid)
            for ap in LxAdsPortfolio.objects.filter(pf_q):
                portfolio_map[f"{ap.portfolio_id}::{ap.profile_id}"] = ap.name or str(ap.portfolio_id)

        # ── 汇率体系（一步查表：LxAdsProfile.currency_code → LxExchangeRate.code）──
        _default_ccy: dict[str, Any] = {"icon": "￥", "code": "CNY", "rate": 1.0}

        # 收集完整筛选集的所有 profile_id 与 currency_code
        all_profile_ids_in_qs = list(qs.values_list("profile_id", flat=True).distinct())
        all_profiles_in_qs = list(LxAdsProfile.objects.filter(profile_id__in=all_profile_ids_in_qs))
        all_currency_codes = {p.currency_code for p in all_profiles_in_qs if p.currency_code}

        # 多货币场景下必须获取 USD 汇率作为统一换算基准；若筛选集中不含美国站点，
        # rate_map_all 中缺少 USD 会导致第 203 行 fallback 到硬编码 7.2，使金额偏差 ~5%。
        if len(all_currency_codes) > 1:
            all_currency_codes.add("USD")

        # 一次查询获取所有相关汇率，每个币种取最新日期记录
        # 生产环境 lx_exchange_rate 表可能尚未建好，查询异常时安全兜底为 _default_ccy
        all_rates: list = []
        try:
            all_rates = list(LxExchangeRate.objects.filter(code__in=all_currency_codes).order_by("-date"))
        except Exception:
            pass
        seen_codes: set[str] = set()
        rate_map_all: dict[str, dict[str, Any]] = {}
        for r in all_rates:
            if r.code not in seen_codes:
                seen_codes.add(r.code)
                rate_map_all[r.code] = {
                    "icon": r.icon or "￥",
                    "code": r.code,
                    "rate": parse_exchange_rate(r.my_rate, r.rate_org),
                }

        # profile_id → 汇率信息的统一映射（全量 + 分页通用）
        profile_to_rate_all: dict[str, dict[str, Any]] = {
            str(p.profile_id): rate_map_all.get(p.currency_code, _default_ccy)
            for p in all_profiles_in_qs
        }

        # 判断是否单一货币，决定汇总行货币基准
        unique_codes: set[str] = {
            rate_map_all.get(c, _default_ccy).get("code", "CNY")
            for c in all_currency_codes
        }
        is_single_currency: bool = len(unique_codes) <= 1

        # 获取美元汇率（多货币时用于统一换算基准）
        usd_rate_info = rate_map_all.get("USD", {"rate": 7.2})
        rate_usd_to_cny: float = float(usd_rate_info.get("rate", 7.2))
        _usd_ccy: dict[str, Any] = {"icon": "$", "code": "USD", "rate": rate_usd_to_cny}

        ref_currency: dict[str, Any] = (
            rate_map_all.get(next(iter(all_currency_codes)), _default_ccy)
            if is_single_currency and all_currency_codes
            else _usd_ccy
        )

        # 当前分页 campaign → 货币信息
        campaign_currency_map: dict[str, dict[str, Any]] = {
            build_campaign_profile_key(item.campaign_id, item.profile_id): profile_to_rate_all.get(
                str(item.profile_id), _default_ccy
            )
            for item in items
        }

        # 多货币时：构建完整查询集下 campaign_id → 货币信息映射（汇总行换算用）
        currency_by_campaign_all: dict[str, dict[str, Any]] = {}
        if not is_single_currency:
            currency_by_campaign_all = {
                build_campaign_profile_key(cid, pid): profile_to_rate_all.get(str(pid), _default_ccy)
                for cid, pid in qs.values_list("campaign_id", "profile_id")
            }

        # 按日期范围聚合指标
        date_start = data.get("date_start")
        date_end = data.get("date_end")
        campaign_pairs = [
            (str(item.campaign_id), str(item.profile_id))
            for item in items
            if item.campaign_id and item.profile_id
        ]

        summary_with_meta = self._build_total_metrics(
            qs, date_start, date_end,
            is_single_currency=is_single_currency,
            ref_currency=ref_currency,
            currency_by_campaign_all=currency_by_campaign_all,
            rate_usd_to_cny=rate_usd_to_cny,
        )
        meta = summary_with_meta.pop("_meta", {})
        summary = summary_with_meta

        metrics_map = self._build_metrics_map(
            campaign_pairs, date_start, date_end,
            total_clicks_all=meta.get("clicks", 0),
            total_impressions_all=meta.get("impressions", 0),
            total_spends_ref=meta.get("spends_ref", 0.0),
            total_ads_sales_ref=meta.get("ads_sales_ref", 0.0),
            campaign_currency_map=campaign_currency_map,
            is_single_currency=is_single_currency,
            rate_usd_to_cny=rate_usd_to_cny,
        )

        res_list = []
        for item in items:
            dic = self._serialize(item)
            p_info = profile_map.get(str(item.profile_id), {})
            dic["profile_alias"] = p_info.get("profile_alias", str(item.profile_id))
            dic["country_name"] = p_info.get("country_name", "-")

            # 兼容前端驼峰命名的列字段配置
            dic["startDate"] = dic.get("start_date")

            # 兼容前端旧字段名：sponsored_type 映射到新字段 campaign_type
            dic["sponsored_type"] = dic.get("campaign_type", "")

            # 兼容前端旧字段名 bidding_type，从 bidding JSONField 中提取 strategy
            bidding_val = dic.get("bidding")
            dic["bidding_type"] = bidding_val.get("strategy", "") if isinstance(bidding_val, dict) else ""

            # 使用 portfolio_id + profile_id 联合键映射出 portfolio_name
            if item.portfolio_id and item.profile_id:
                pf_key = f"{item.portfolio_id}::{item.profile_id}"
                dic["portfolio_name"] = portfolio_map.get(pf_key, "")
            else:
                dic["portfolio_name"] = ""

            # 服务状态：后端统一解析，前端直接渲染
            _ss = resolve_service_status(item.serving_status)
            dic["service_status_label"] = _ss["label"]
            dic["service_status_type"] = _ss["type"]

            # 填充聚合后的指标数据
            dic.update(
                metrics_map.get(
                    build_campaign_profile_key(item.campaign_id, item.profile_id),
                    self._empty_metrics(),
                )
            )

            # 补充 LxAdsProfile.sid（店铺 ID，旧 store_id 字段）
            dic["store_id"] = p_info.get("sid", "")

            res_list.append(dic)

        result = {
            "total": total,
            "list": res_list,
            "summary": summary,
            "pageNum": p_num,
            "pageSize": p_size,
        }
        return drf_ok(result)

    @action(detail=False, methods=["get"], url_path="campaign-info")
    def campaign_info(self, request: Request) -> Response:
        """根据 ``campaign_id`` 与 ``profile_id`` 返回单条 SP 广告活动基础信息。

        主要供详情页面加载面包屑标题与投放类型使用，不包含指标数据。

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
        """
        campaign_id = request.query_params.get("campaign_id", "").strip()
        profile_id = request.query_params.get("profile_id", "").strip()

        if not campaign_id or not profile_id:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        try:
            obj = LxSpCampaign.objects.get(campaign_id=campaign_id, profile_id=profile_id)
        except LxSpCampaign.DoesNotExist:
            return drf_ok({}, msg="未找到对应的广告活动")

        return drf_ok({
            "campaign_id": obj.campaign_id,
            "name": obj.name,
            "targeting_type": obj.targeting_type or "",
            "state": obj.state,
            "sponsored_type": obj.campaign_type,
        })

    @staticmethod
    def _empty_metrics() -> dict[str, Any]:
        """返回指标字段的空默认值，供无指标数据的广告活动填充占位。"""
        return {
            "adsSales": "-",
            "adsSalesPercent": "-",
            "directSales": "-",
            "adsOrders": "-",
            "directOrders": "-",
            "adsVolume": "-",
            "adsOrderPrice": "-",
            "is": "-",
            "acos": "-",
            "roas": "-",
            "cvr": "-",
            "impressions": "-",
            "impressionsPercent": "-",
            "clicks": "-",
            "clicksPercent": "-",
            "ctr": "-",
            "cpc": "-",
            "spends": "-",
            "spendsPercent": "-",
            "cpa": "-",
        }

    @staticmethod
    def _build_metrics_map(
        campaign_pairs: list[tuple[str, str]],
        date_start: str | None,
        date_end: str | None,
        *,
        total_clicks_all: int = 0,
        total_impressions_all: int = 0,
        total_spends_ref: float = 0.0,
        total_ads_sales_ref: float = 0.0,
        campaign_currency_map: dict[str, dict[str, Any]],
        is_single_currency: bool,
        rate_usd_to_cny: float = 1.0,
    ) -> dict[str, dict[str, Any]]:
        """按日期范围聚合 SP 广告活动报表指标，计算所有衍生指标与占比字段，并为价格类字段附加货币符号。

        全部计算在后端完成，前端直接展示结果。

        Args:
            campaign_pairs (list[tuple[str, str]]): 当前分页的 (campaign_id, profile_id) 复合键列表。
            date_start (str | None): 起始日期（YYYY-MM-DD）。
            date_end (str | None): 截止日期（YYYY-MM-DD）。
            total_clicks_all (int): 全量筛选集的点击总数，用于计算分页内各行的点击占比。
            total_impressions_all (int): 全量筛选集的曝光总数，用于计算分页内各行的曝光占比。
            total_spends_ref (float): 全量筛选集的花费基准值（已换算为参考货币），用于计算花费占比。
            total_ads_sales_ref (float): 全量筛选集的广告销售额基准值（已换算为参考货币），用于计算销售额占比。
            campaign_currency_map (dict[str, dict]): campaign 复合键 → 货币信息（icon, code, rate）。
            is_single_currency (bool): 是否仅含单一货币。
            rate_usd_to_cny (float): 美元对人民币汇率，用于多货币时各本地货币换算为美元基准。

        Returns:
            dict[str, dict[str, Any]]: campaign 复合键 → 格式化后的指标字典。
        """
        if not campaign_pairs:
            return {}

        qs = LxSpCampaignReport.objects.filter(build_campaign_profile_query(campaign_pairs))
        if date_start:
            qs = qs.filter(report_date__gte=date_start)
        if date_end:
            qs = qs.filter(report_date__lte=date_end)

        agg_rows = qs.values("campaign_id", "profile_id").annotate(
            total_sales=Sum("sales"),
            total_same_sales=Sum("same_sales"),
            total_orders=Sum("orders"),
            total_same_orders=Sum("same_orders"),
            total_units=Sum("units"),
            total_cost=Sum("cost"),
            total_clicks=Sum("clicks"),
            total_impressions=Sum("impressions"),
        )

        result: dict[str, dict[str, Any]] = {}
        for row in agg_rows:
            row_key = build_campaign_profile_key(row["campaign_id"], row["profile_id"])
            ccy = campaign_currency_map.get(row_key, {"icon": "$", "code": "USD", "rate": rate_usd_to_cny})
            # 各行展示值始终使用本国货币符号与本地金额，多货币时不做换算
            icon: str = ccy["icon"]

            # rate 仅用于占比（%）计算时对齐参考基准
            # 单一货币：rate = 1.0（本地金额直接参与占比计算）
            # 多货币：rate = 本地货币对人民币汇率 ÷ 美元对人民币汇率（将本地金额换算为美元基准）
            rate: float = (ccy["rate"] / rate_usd_to_cny) if not is_single_currency else 1.0

            row_cost = float(row["total_cost"] or 0)
            row_sales = float(row["total_sales"] or 0)
            row_orders = int(row["total_orders"] or 0)
            row_clicks = int(row["total_clicks"] or 0)
            row_impressions = int(row["total_impressions"] or 0)
            row_same_sales = float(row["total_same_sales"] or 0)

            # 仅用于与汇总行（全量美元基准）做占比比较，不对外展示
            ref_sales = row_sales * rate
            ref_spends = row_cost * rate

            acos = f"{round(row_cost / row_sales * 100, 2)}%" if row_sales > 0 else "-"
            roas = round(row_sales / row_cost, 2) if row_cost > 0 else "-"
            cvr = f"{round(row_orders / row_clicks * 100, 2)}%" if row_clicks > 0 else "-"
            ads_sales_percent = (
                f"{round(ref_sales / total_ads_sales_ref * 100, 2)}%"
                if total_ads_sales_ref > 0
                else "-"
            )
            cpc_raw = round(row_cost / row_clicks, 2) if row_clicks > 0 else None
            ctr = f"{round(row_clicks / row_impressions * 100, 2)}%" if row_impressions > 0 else "-"
            cpa_raw = round(row_cost / row_orders, 2) if row_orders > 0 else None

            result[row_key] = {
                "adsSales": fmt_money(row_sales, icon),
                "adsSalesPercent": ads_sales_percent,
                "directSales": fmt_money(row_same_sales, icon),
                "adsOrders": row_orders,
                "directOrders": int(row["total_same_orders"] or 0),
                "adsVolume": int(row["total_units"] or 0),
                "adsOrderPrice": fmt_money(round(row_sales / row_orders, 2), icon) if row_orders > 0 else "-",
                "is": "---",
                "acos": acos,
                "roas": roas,
                "cvr": cvr,
                "impressions": row_impressions,
                "impressionsPercent": (
                    f"{round(row_impressions / total_impressions_all * 100, 2)}%"
                    if total_impressions_all > 0
                    else "-"
                ),
                "clicks": row_clicks,
                "clicksPercent": (
                    f"{round(row_clicks / total_clicks_all * 100, 2)}%"
                    if total_clicks_all > 0
                    else "-"
                ),
                "ctr": ctr,
                "cpc": fmt_money(cpc_raw, icon) if cpc_raw is not None else "-",
                "spends": fmt_money(row_cost, icon),
                "spendsPercent": (
                    f"{round(ref_spends / total_spends_ref * 100, 2)}%"
                    if total_spends_ref > 0
                    else "-"
                ),
                "cpa": fmt_money(cpa_raw, icon) if cpa_raw is not None else "-",
            }

        return result

    @staticmethod
    def _build_total_metrics(
        campaign_ids_qs: Any,
        date_start: str | None,
        date_end: str | None,
        *,
        is_single_currency: bool,
        ref_currency: dict[str, Any],
        currency_by_campaign_all: dict[str, dict[str, Any]],
        rate_usd_to_cny: float = 1.0,
    ) -> dict[str, Any]:
        """对完整筛选结果集进行全量指标聚合，用于构建表格汇总行与占比基准值。

        - 单一货币时：直接聚合，使用该货币符号。
        - 多货币时：按 campaign 分组聚合后，依 ``rate ÷ rate_usd_to_cny`` 统一换算为美元（USD）再汇总。

        Args:
            campaign_ids_qs (QuerySet): 完整筛选结果的 LxSpCampaign QuerySet。
            date_start (str | None): 起始日期。
            date_end (str | None): 截止日期。
            is_single_currency (bool): 是否仅含单一货币。
            ref_currency (dict): 参考货币信息（icon / code / rate）。
            currency_by_campaign_all (dict): 全量 campaign → 货币信息映射（多货币时传入）。
            rate_usd_to_cny (float): 美元对人民币汇率。

        Returns:
            dict[str, Any]: 汇总行指标字段，含 _meta 内部基准值（不对外暴露）。
        """
        icon: str = ref_currency["icon"]

        # Step 1：拉取所有有效 (campaign_id, profile_id) 复合键集合（1 次轻量查询）
        all_pairs_set: set[tuple[str, str]] = {
            (str(cid), str(pid))
            for cid, pid in campaign_ids_qs.values_list("campaign_id", "profile_id")
        }

        if not all_pairs_set:
            return {
                "adsSales": "-",
                "adsSalesPercent": "-",
                "directSales": "-",
                "adsOrders": 0,
                "directOrders": 0,
                "adsVolume": 0,
                "adsOrderPrice": "-",
                "is": "---",
                "acos": "-",
                "roas": "-",
                "cvr": "-",
                "impressions": 0,
                "impressionsPercent": "-",
                "clicks": 0,
                "clicksPercent": "-",
                "ctr": "-",
                "cpc": "-",
                "spends": "-",
                "spendsPercent": "-",
                "cpa": "-",
                "_meta": {
                    "ads_sales_ref": 0.0,
                    "spends_ref": 0.0,
                    "clicks": 0,
                    "impressions": 0,
                },
            }

        # Step 2：双字段 IN 过滤报表表（仅 1 次 DB 查询）
        all_campaign_ids = list({cid for cid, _ in all_pairs_set})
        all_profile_ids = list({pid for _, pid in all_pairs_set})

        base_qs = LxSpCampaignReport.objects.filter(
            campaign_id__in=all_campaign_ids,
            profile_id__in=all_profile_ids,
        )
        if date_start:
            base_qs = base_qs.filter(report_date__gte=date_start)
        if date_end:
            base_qs = base_qs.filter(report_date__lte=date_end)

        # Step 3：DB 端按 (campaign_id, profile_id) 分组聚合（1 次 SQL，DB 端完成所有 SUM）
        per_campaign = base_qs.values("campaign_id", "profile_id").annotate(
            s_sales=Sum("sales"),
            s_same_sales=Sum("same_sales"),
            s_orders=Sum("orders"),
            s_same_orders=Sum("same_orders"),
            s_units=Sum("units"),
            s_cost=Sum("cost"),
            s_clicks=Sum("clicks"),
            s_impressions=Sum("impressions"),
        )

        t_sales = t_same_sales = t_cost = 0.0
        t_orders = t_same_orders = t_units = t_clicks = t_impressions = 0

        # Step 4：Python 端过滤有效对 + 汇率换算累加
        for row in per_campaign:
            pair_key = (str(row["campaign_id"]), str(row["profile_id"]))
            if pair_key not in all_pairs_set:
                # 排除跨店同 campaign_id 碰撞产生的极少数误匹配行
                continue

            if not is_single_currency:
                row_key = build_campaign_profile_key(row["campaign_id"], row["profile_id"])
                ccy = currency_by_campaign_all.get(row_key, {"rate": rate_usd_to_cny})
                # 本地货币 → 人民币 → 美元：rate / rate_usd_to_cny
                rate = ccy.get("rate", rate_usd_to_cny) / rate_usd_to_cny
                t_sales += float(row["s_sales"] or 0) * rate
                t_same_sales += float(row["s_same_sales"] or 0) * rate
                t_cost += float(row["s_cost"] or 0) * rate
            else:
                t_sales += float(row["s_sales"] or 0)
                t_same_sales += float(row["s_same_sales"] or 0)
                t_cost += float(row["s_cost"] or 0)

            t_orders += int(row["s_orders"] or 0)
            t_same_orders += int(row["s_same_orders"] or 0)
            t_units += int(row["s_units"] or 0)
            t_clicks += int(row["s_clicks"] or 0)
            t_impressions += int(row["s_impressions"] or 0)

        # 衍生指标计算（与货币无关的公式对单/多货币均适用）
        acos = f"{round(t_cost / t_sales * 100, 2)}%" if t_sales > 0 else "-"
        roas = round(t_sales / t_cost, 2) if t_cost > 0 else "-"
        cvr = f"{round(t_orders / t_clicks * 100, 2)}%" if t_clicks > 0 else "-"
        ctr = f"{round(t_clicks / t_impressions * 100, 2)}%" if t_impressions > 0 else "-"
        cpc_raw = round(t_cost / t_clicks, 2) if t_clicks > 0 else None
        cpa_raw = round(t_cost / t_orders, 2) if t_orders > 0 else None

        return {
            "adsSales": fmt_money(t_sales, icon),
            "adsSalesPercent": "100%" if t_sales > 0 else "-",
            "directSales": fmt_money(t_same_sales, icon),
            "adsOrders": t_orders,
            "directOrders": t_same_orders,
            "adsVolume": t_units,
            "adsOrderPrice": fmt_money(round(t_sales / t_orders, 2), icon) if t_orders > 0 else "-",
            "is": "---",
            "acos": acos,
            "roas": roas,
            "cvr": cvr,
            "impressions": t_impressions,
            "impressionsPercent": "100%" if t_impressions > 0 else "-",
            "clicks": t_clicks,
            "clicksPercent": "100%" if t_clicks > 0 else "-",
            "ctr": ctr,
            "cpc": fmt_money(cpc_raw, icon) if cpc_raw is not None else "-",
            "spends": fmt_money(t_cost, icon),
            "spendsPercent": "100%" if t_cost > 0 else "-",
            "cpa": fmt_money(cpa_raw, icon) if cpa_raw is not None else "-",
            # 内部原始数值，在 list 方法中弹出，不发往前端
            "_meta": {
                "ads_sales_ref": round(t_sales, 6),
                "spends_ref": round(t_cost, 6),
                "clicks": t_clicks,
                "impressions": t_impressions,
            },
        }
