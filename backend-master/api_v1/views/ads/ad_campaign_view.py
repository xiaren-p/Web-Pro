"""广告活动基础数据视图（LxCampaignInfo），仅提供查询。"""
from __future__ import annotations

from typing import Any

from django.db.models import FloatField, Max, Q, Sum, Value
from django.db.models.functions import Cast, NullIf
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import (
    CurrencyIcon,
    LxAdPortfolios,
    LxCampaignInfo,
    LxCampaignMetrics,
    LxCurrencyRates,
    LxShopProfile,
)
from api_v1.serializers import LxCampaignInfoSerializer
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok
from api_v1.views.ads._helpers import (
    COUNTRY_MAP,
    build_campaign_profile_key,
    build_campaign_profile_query,
    fmt_money,
)


class AdCampaignViewSet(viewsets.ViewSet):
    """广告活动基础数据视图（只提供查询）。"""

    def _serialize(self, obj: LxCampaignInfo) -> dict[str, Any]:
        """数据序列化辅助方法。

        Args:
            obj (LxCampaignInfo): 广告活动对象基类。

        Returns:
            dict[str, Any]: 序列化后的合法字典。
        """
        return LxCampaignInfoSerializer(obj).data

    @action(detail=False, methods=["post"], url_path="list")
    def list(self, request: Request) -> Response:
        """分页获取广告活动列表及指标详情。

        接受复合的检索参数并在底层合并广告表及其归属的国家和店铺数据。

        Args:
            request (Request): DRF 原始请求对象。

        Returns:
            Response: 组合映射好 ``profile_alias`` 等补充数据的标准分页结果集。
        """
        qs = LxCampaignInfo.objects.all().order_by("-start_date")

        # 将所有的 GET query_params 替换为 POST 的 data 获取参数
        data = request.data

        keyword = data.get("keyword") or data.get("name")
        if isinstance(keyword, str) and keyword.strip():
            kw = keyword.strip()
            qs = qs.filter(
                Q(name__icontains=kw)
                | Q(store_id__icontains=kw)
                | Q(campaign_id__icontains=kw)
            )

        state = data.get("state")
        if state:
            qs = qs.filter(state__in=state.split(","))

        service_status = data.get("service_status")
        if service_status:
            qs = qs.filter(service_status__in=service_status.split(","))

        sponsored_type = data.get("sponsored_type")
        if sponsored_type:
            qs = qs.filter(sponsored_type__in=sponsored_type.split(","))

        bidding_type = data.get("bidding_type")
        if bidding_type:
            qs = qs.filter(bidding_type__in=bidding_type.split(","))

        portfolio_id = data.get("portfolio_id")
        if portfolio_id:
            p_ids = [p for p in portfolio_id.split(",") if p]
            if "-1" in p_ids:
                p_ids.remove("-1")
                if p_ids:
                    qs = qs.filter(Q(portfolio_id__in=p_ids) | Q(portfolio_id__isnull=True) | Q(portfolio_id=""))
                else:
                    qs = qs.filter(Q(portfolio_id__isnull=True) | Q(portfolio_id=""))
            else:
                qs = qs.filter(portfolio_id__in=p_ids)

        profiles = data.get("profiles")
        if profiles:
            qs = qs.filter(profile_id__in=profiles.split(","))

        countries = data.get("countries")
        if countries:
            shop_qs = LxShopProfile.objects.filter(country__in=countries.split(","))
            profile_ids = shop_qs.values_list("profile_id", flat=True)
            qs = qs.filter(profile_id__in=profile_ids)

        sort_prop = data.get("sort_prop")
        sort_order = data.get("sort_order")
        if sort_prop and sort_order in ["asc", "desc"]:
            field_map = {
                "overBudgetTime": "last_over_budget_at",
                "startDate": "start_date",
            }
            db_field = field_map.get(sort_prop, sort_prop)
            order_prefix = "-" if sort_order == "desc" else ""
            try:
                qs = qs.order_by(f"{order_prefix}{db_field}")
            except Exception:
                pass

        total, items, p_num, p_size = paginate_queryset(request, qs)

        # 组装店铺与国家数据
        item_profile_ids = [item.profile_id for item in items if item.profile_id]
        shop_profiles = LxShopProfile.objects.filter(profile_id__in=item_profile_ids)

        profile_map: dict[str, dict[str, str]] = {}
        for sp in shop_profiles:
            country = sp.country or ""
            c_name = COUNTRY_MAP.get(country.upper(), country)
            # 注意：LxShopProfile.profile_id 在数据库实际为 BIGINT，ORM 返回 int 类型；
            # LxCampaignInfo.profile_id 为 VARCHAR，ORM 返回 str 类型。
            # 统一转为 str 作为字典键，防止类型不一致导致永远匹配不上。
            profile_map[str(sp.profile_id)] = {
                "profile_alias": sp.alias if sp.alias else str(sp.profile_id),
                "country_name": c_name,
            }

        # 组装广告组合数据
        item_portfolio_ids = [item.portfolio_id for item in items if item.portfolio_id]
        ad_portfolios = LxAdPortfolios.objects.filter(portfolio_id__in=item_portfolio_ids)
        portfolio_map: dict[str, str] = {str(p.portfolio_id): p.name or str(p.portfolio_id) for p in ad_portfolios}

        # ── 货币汇率初始化（两步查表：country_icon → code → lx_currency_rates）────
        # 默认货币为人民币（找不到匹配时的安全 fallback）
        _default_ccy: dict[str, Any] = {"icon": "￥", "code": "CNY", "rate": 1.0}

        # Step 1：从 currency_icon 表建立 国家码 → 货币代码 映射
        country_to_code: dict[str, str] = {ci.country: ci.code for ci in CurrencyIcon.objects.all()}

        # Step 2：从 lx_currency_rates 表建立 货币代码 → {icon, code, rate} 映射
        all_cr = list(LxCurrencyRates.objects.all())
        code_to_rate: dict[str, dict[str, Any]] = {
            cr.code: {
                "icon": cr.icon or "￥",
                "code": cr.code or "CNY",
                "rate": float(cr.rate or 1.0),
            }
            for cr in all_cr
            if cr.code
        }

        # 合并：国家码 → {icon, code, rate}（经 currency_icon.code 二次关联）
        rates_by_country: dict[str, dict[str, Any]] = {
            country: code_to_rate[code]
            for country, code in country_to_code.items()
            if code in code_to_rate
        }

        # 获取美元对人民币汇率，用于多货币时将各本地货币统一换算为美元
        _usd_cr = next((cr for cr in all_cr if cr.code == "USD"), None)
        rate_usd_to_cny: float = float(_usd_cr.rate) if _usd_cr and _usd_cr.rate else 7.2
        # 多货币汇总行以美元为参考单位
        _usd_ccy: dict[str, Any] = {"icon": "$", "code": "USD", "rate": rate_usd_to_cny}
        # 当前分页：从已查询的 shop_profiles 中提取 profile_id → 国家代码映射
        country_by_profile_page: dict[str, str] = {
            str(sp.profile_id): (sp.country or "") for sp in shop_profiles
        }

        # 当前分页的 campaign_id → 货币信息映射（含 rate 字段）
        campaign_currency_map: dict[str, dict[str, Any]] = {
            build_campaign_profile_key(item.campaign_id, item.profile_id): rates_by_country.get(
                country_by_profile_page.get(str(item.profile_id), ""), _default_ccy
            )
            for item in items
        }

        # 判断完整筛选结果集是否仅含单一货币（决定汇总行是否需要汇率换算）
        all_profile_ids_in_qs: list = list(qs.values_list("profile_id", flat=True).distinct())
        all_countries_in_qs: set[str] = set(
            LxShopProfile.objects.filter(profile_id__in=all_profile_ids_in_qs).values_list("country", flat=True)
        )
        unique_codes: set[str] = {
            rates_by_country.get(c, _default_ccy).get("code", "CNY")
            for c in all_countries_in_qs
            if c
        }
        is_single_currency: bool = len(unique_codes) <= 1
        ref_currency: dict[str, Any] = (
            rates_by_country.get(next(iter(all_countries_in_qs)), _default_ccy)
            if is_single_currency and all_countries_in_qs
            else _usd_ccy
        )

        # 多货币时：构建完整查询集下 campaign_id → 货币信息映射（含 rate）
        currency_by_campaign_all: dict[str, dict[str, Any]] = {}
        if not is_single_currency:
            all_profiles_full: dict[str, str] = {
                str(sp.profile_id): (sp.country or "")
                for sp in LxShopProfile.objects.filter(profile_id__in=all_profile_ids_in_qs)
            }
            currency_by_campaign_all = {
                build_campaign_profile_key(cid, pid): rates_by_country.get(
                    all_profiles_full.get(str(pid), ""), _default_ccy
                )
                for cid, pid in qs.values_list("campaign_id", "profile_id")
            }

        # 按日期范围聚合指标：同组内累加数值型字段，IS 和笔单价取最大值
        date_start = data.get("date_start")
        date_end = data.get("date_end")
        campaign_pairs = [
            (str(item.campaign_id), str(item.profile_id))
            for item in items
            if item.campaign_id and item.profile_id
        ]

        # 先计算全量汇总，并从 _meta 中提取各基准值后传入 _build_metrics_map
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
            dic["profile_alias"] = p_info.get("profile_alias", item.profile_id)
            dic["country_name"] = p_info.get("country_name", "-")

            # 兼容前端驼峰命名的列字段配置
            dic["overBudgetTime"] = dic.get("last_over_budget_at")
            dic["startDate"] = dic.get("start_date")

            # 使用 portfolio_id 映射出 portfolio_name
            if item.portfolio_id:
                dic["portfolio_name"] = portfolio_map.get(str(item.portfolio_id), "")
            else:
                dic["portfolio_name"] = ""

            # 服务状态：后端统一解析，前端直接渲染，无需客户端映射
            _ss = resolve_service_status(item.service_status)
            dic["service_status_label"] = _ss["label"]
            dic["service_status_type"] = _ss["type"]

            # 填充聚合后的指标数据（含占比字段，全部在 _build_metrics_map 内计算完成）
            dic.update(
                metrics_map.get(
                    build_campaign_profile_key(item.campaign_id, item.profile_id),
                    self._empty_metrics(),
                )
            )

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
        """根据 ``campaign_id`` 与 ``profile_id`` 返回单条广告活动基础信息。

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
            - sponsored_type (str): 广告类型。
        """
        campaign_id = request.query_params.get("campaign_id", "").strip()
        profile_id = request.query_params.get("profile_id", "").strip()

        if not campaign_id or not profile_id:
            return drf_ok({}, msg="campaign_id 与 profile_id 均为必填参数")

        try:
            obj = LxCampaignInfo.objects.get(campaign_id=campaign_id, profile_id=profile_id)
        except LxCampaignInfo.DoesNotExist:
            return drf_ok({}, msg="未找到对应的广告活动")

        return drf_ok({
            "campaign_id": obj.campaign_id,
            "name": obj.name,
            "targeting_type": obj.targeting_type or "",
            "state": obj.state,
            "sponsored_type": obj.sponsored_type,
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
        """按日期范围聚合广告活动指标，计算所有衍生指标与占比字段，并为价格类字段附加货币符号。

        全部计算在后端完成，前端直接展示结果。
        """
        if not campaign_pairs:
            return {}

        qs = LxCampaignMetrics.objects.filter(build_campaign_profile_query(campaign_pairs))
        if date_start:
            qs = qs.filter(timestamp__gte=date_start)
        if date_end:
            qs = qs.filter(timestamp__lte=date_end)

        # top_of_search_impression_share 为 varchar，空字符串需转为 NULL 后再取最大值
        agg_rows = qs.values("campaign_id", "profile_id").annotate(
            total_sales=Sum("sales"),
            total_direct_sales=Sum("direct_sales"),
            total_orders=Sum("orders"),
            total_direct_orders=Sum("direct_orders"),
            total_ad_units=Sum("ad_units"),
            total_spends=Sum("spends"),
            total_clicks=Sum("clicks"),
            total_impressions=Sum("impressions"),
            # IS 字段：NULLIF 过滤空串后转数值取最大值
            max_is=Max(
                Cast(
                    NullIf("top_of_search_impression_share", Value("")),
                    output_field=FloatField(),
                )
            ),
        )

        result: dict[str, dict[str, Any]] = {}
        for row in agg_rows:
            row_key = build_campaign_profile_key(row["campaign_id"], row["profile_id"])
            ccy = campaign_currency_map.get(row_key, {"icon": "$", "code": "USD", "rate": rate_usd_to_cny})
            # 各行展示值始终使用本国货币符号与本地金额，多货币时不做换算
            icon: str = ccy["icon"]

            # rate 仅用于占比（%）计算时对齐参考基准（单一货币=1.0；多货币=本地→USD换算系数）
            rate: float = (ccy["rate"] / rate_usd_to_cny) if not is_single_currency else 1.0

            row_spends = float(row["total_spends"] or 0)
            row_sales = float(row["total_sales"] or 0)
            row_orders = int(row["total_orders"] or 0)
            row_clicks = int(row["total_clicks"] or 0)
            row_impressions = int(row["total_impressions"] or 0)
            row_direct_sales = float(row["total_direct_sales"] or 0)

            # 仅用于与汇总行（全量美元基准）做占比比较，不对外展示
            ref_sales = row_sales * rate
            ref_spends = row_spends * rate

            acos = f"{round(row_spends / row_sales * 100, 2)}%" if row_sales > 0 else "-"
            roas = round(row_sales / row_spends, 2) if row_spends > 0 else "-"
            cvr = f"{round(row_orders / row_clicks * 100, 2)}%" if row_clicks > 0 else "-"
            ads_sales_percent = (
                f"{round(ref_sales / total_ads_sales_ref * 100, 2)}%"
                if total_ads_sales_ref > 0
                else "-"
            )
            cpc_raw = round(row_spends / row_clicks, 2) if row_clicks > 0 else None
            ctr = f"{round(row_clicks / row_impressions * 100, 2)}%" if row_impressions > 0 else "-"
            cpa_raw = round(row_spends / row_orders, 2) if row_orders > 0 else None

            result[row_key] = {
                "adsSales": fmt_money(row_sales, icon),
                "adsSalesPercent": ads_sales_percent,
                "directSales": fmt_money(row_direct_sales, icon),
                "adsOrders": row_orders,
                "directOrders": int(row["total_direct_orders"] or 0),
                "adsVolume": int(row["total_ad_units"] or 0),
                "adsOrderPrice": fmt_money(round(row_sales / row_orders, 2), icon) if row_orders > 0 else "-",
                "is": f"{round(float(row['max_is']), 2)}%" if row["max_is"] is not None else "-",
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
                "spends": fmt_money(row_spends, icon),
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

        # Step 2：双字段 IN 过滤指标表（仅 1 次 DB 查询）
        all_campaign_ids = list({cid for cid, _ in all_pairs_set})
        all_profile_ids = list({pid for _, pid in all_pairs_set})

        base_qs = LxCampaignMetrics.objects.filter(
            campaign_id__in=all_campaign_ids,
            profile_id__in=all_profile_ids,
        )
        if date_start:
            base_qs = base_qs.filter(timestamp__gte=date_start)
        if date_end:
            base_qs = base_qs.filter(timestamp__lte=date_end)

        # Step 3：DB 端按 (campaign_id, profile_id) 分组聚合（1 次 SQL，DB 端完成所有 SUM）
        per_campaign = base_qs.values("campaign_id", "profile_id").annotate(
            s_sales=Sum("sales"),
            s_direct_sales=Sum("direct_sales"),
            s_orders=Sum("orders"),
            s_direct_orders=Sum("direct_orders"),
            s_ad_units=Sum("ad_units"),
            s_spends=Sum("spends"),
            s_clicks=Sum("clicks"),
            s_impressions=Sum("impressions"),
        )

        t_sales = t_direct_sales = t_spends = 0.0
        t_orders = t_direct_orders = t_ad_units = t_clicks = t_impressions = 0

        # Step 4：Python 端过滤有效对 + 汇率换算累加
        for row in per_campaign:
            pair_key = (str(row["campaign_id"]), str(row["profile_id"]))
            if pair_key not in all_pairs_set:
                continue  # 排除跨店同 campaign_id 碰撞产生的极少数误匹配行

            if not is_single_currency:
                row_key = build_campaign_profile_key(row["campaign_id"], row["profile_id"])
                ccy = currency_by_campaign_all.get(row_key, {"rate": rate_usd_to_cny})
                # 本地货币 → 人民币 → 美元：rate / rate_usd_to_cny
                rate = ccy.get("rate", rate_usd_to_cny) / rate_usd_to_cny
                t_sales += float(row["s_sales"] or 0) * rate
                t_direct_sales += float(row["s_direct_sales"] or 0) * rate
                t_spends += float(row["s_spends"] or 0) * rate
            else:
                t_sales += float(row["s_sales"] or 0)
                t_direct_sales += float(row["s_direct_sales"] or 0)
                t_spends += float(row["s_spends"] or 0)

            t_orders += int(row["s_orders"] or 0)
            t_direct_orders += int(row["s_direct_orders"] or 0)
            t_ad_units += int(row["s_ad_units"] or 0)
            t_clicks += int(row["s_clicks"] or 0)
            t_impressions += int(row["s_impressions"] or 0)

        # 衍生指标计算（与货币无关的公式对单/多货币均适用）
        acos = f"{round(t_spends / t_sales * 100, 2)}%" if t_sales > 0 else "-"
        roas = round(t_sales / t_spends, 2) if t_spends > 0 else "-"
        cvr = f"{round(t_orders / t_clicks * 100, 2)}%" if t_clicks > 0 else "-"
        ctr = f"{round(t_clicks / t_impressions * 100, 2)}%" if t_impressions > 0 else "-"
        cpc_raw = round(t_spends / t_clicks, 2) if t_clicks > 0 else None
        cpa_raw = round(t_spends / t_orders, 2) if t_orders > 0 else None

        return {
            "adsSales": fmt_money(t_sales, icon),
            "adsSalesPercent": "100%" if t_sales > 0 else "-",
            "directSales": fmt_money(t_direct_sales, icon),
            "adsOrders": t_orders,
            "directOrders": t_direct_orders,
            "adsVolume": t_ad_units,
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
            "spends": fmt_money(t_spends, icon),
            "spendsPercent": "100%" if t_spends > 0 else "-",
            "cpa": fmt_money(cpa_raw, icon) if cpa_raw is not None else "-",
            # 内部原始数值，在 list 方法中弹出，不发往前端
            "_meta": {
                "ads_sales_ref": round(t_sales, 6),
                "spends_ref": round(t_spends, 6),
                "clicks": t_clicks,
                "impressions": t_impressions,
            },
        }
