"""SP 广告活动列表查询选择器。

从 ``ad_campaign_view`` 提取完整的分页查询、Doris 聚合、指标计算、
数据组装逻辑。视图层仅保留请求解析与响应装配。
"""
from __future__ import annotations

from typing import Any

from django.db.models import Q, Sum

from apps.ads.models.lx_ads_portfolio import LxAdsPortfolio
from apps.ads.models.lx_ads_profile import LxAdsProfile
from apps.ads.sp.models.lx_sp_ad import LxSpAd
from apps.ads.sp.models.lx_sp_campaign import LxSpCampaign
from apps.ads.sp.models.lx_sp_campaign_report import LxSpCampaignReport
from apps.ads.sp.selectors.campaign_ref_selectors import (
    get_profile_map, get_sid_country_map, get_rate_map,
    get_tag_asin_map, get_owner_asin_map, get_asin_info_map,
    get_asin_cp_map, get_sku_cp_map,
)
from apps.ads.sp.rules.models.sp_campaign_adjustment import (
    CampaignExecutionTypeChoices, SpCampaignAdjustment,
)
from apps.ads.utils.ad_status import resolve_service_status
from apps.ads.views._helpers import (
    BIDDING_STRATEGY_LABEL, CAMPAIGN_TYPE_SHORT,
    build_campaign_profile_key, build_campaign_profile_query,
)
from apps.sales.listing.models.lx_listing_tag import LxListingTag
from apps.sales.listing.models.lx_listing_data import LxListingData


def build_campaign_list_data(params: dict) -> dict:
    """构建 SP 广告活动分页列表数据。

    包含多维筛选（关键词/状态/类型/竞价策略/标签/负责人/组合/店铺/国家/SKU）、
    Doris 聚合、排序分页、指标计算、标签/负责人/调整信息富化。

    Args:
        params (dict): request.data 字典。

    Returns:
        dict: 可直接序列化返回给前端的完整结果。
    """
    qs = LxSpCampaign.objects.all().order_by("-start_date")

    keyword = params.get("keyword") or params.get("name")
    if isinstance(keyword, str) and keyword.strip():
        kw = keyword.strip()
        base_q = Q(name__icontains=kw)
        try:
            base_q |= Q(campaign_id=int(kw))
        except (ValueError, TypeError):
            pass
        matched_pids = list(
            LxAdsProfile.objects.filter(sid__icontains=kw).values_list("profile_id", flat=True)
        )
        if matched_pids:
            base_q |= Q(profile_id__in=matched_pids)
        qs = qs.filter(base_q)

    state = params.get("state")
    if state:
        qs = qs.filter(state__in=state.split(","))

    serving_status = params.get("service_status")
    if serving_status:
        qs = qs.filter(serving_status__in=serving_status.split(","))

    campaign_type = params.get("sponsored_type")
    if campaign_type:
        qs = qs.filter(campaign_type__in=campaign_type.split(","))

    bidding_strategy = params.get("bidding_type")
    if bidding_strategy:
        qs = qs.filter(bidding__strategy__in=bidding_strategy.split(","))

    # 标签筛选
    tag_cp_keys: set[str] | None = None
    tags = params.get("tags")
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            tag_gids = list(LxListingTag.objects.filter(
                tag_name__in=tag_list, status="normal"
            ).values_list("global_tag_id", flat=True))
            if tag_gids:
                tag_asin_cache = get_tag_asin_map()
                tag_asins: set[str] = set()
                for gid in tag_gids:
                    gid_str = str(gid)
                    if gid_str and gid_str in tag_asin_cache:
                        tag_asins |= tag_asin_cache[gid_str]
                if tag_asins:
                    asin_cp_map = get_asin_cp_map()
                    tag_cp_keys = set()
                    for asin_val in tag_asins:
                        tag_cp_keys |= asin_cp_map.get(asin_val, set())
                else:
                    tag_cp_keys = set()
            else:
                tag_cp_keys = set()

    # 负责人筛选
    owner_cp_keys: set[str] | None = None
    owner_ids = params.get("owners")
    if owner_ids:
        owner_list = [str(o).strip() for o in owner_ids.split(",") if str(o).strip()]
        if owner_list:
            owner_asin_cache = get_owner_asin_map()
            owner_asins: set[str] = set()
            for uid in owner_list:
                if uid in owner_asin_cache:
                    owner_asins |= owner_asin_cache[uid]
            if owner_asins:
                asin_cp_map = get_asin_cp_map()
                owner_cp_keys = set()
                for asin_val in owner_asins:
                    owner_cp_keys |= asin_cp_map.get(asin_val, set())
            else:
                owner_cp_keys = set()

    portfolio_id = params.get("portfolio_id")
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

    profiles = params.get("profiles")
    if profiles:
        qs = qs.filter(profile_id__in=profiles.split(","))

    countries = params.get("countries")
    if countries:
        profile_ids = LxAdsProfile.objects.filter(
            country_code__in=countries.split(",")
        ).values_list("profile_id", flat=True)
        qs = qs.filter(profile_id__in=profile_ids)

    # ASIN / MSKU / parent_asin 搜索
    search_cp_keys: set[str] | None = None
    skus = params.get("skus")
    asin_search_type = params.get("asinSearchType", "sku")
    if skus:
        sku_list = [s.strip() for s in skus.split(",") if s.strip()]
        if sku_list:
            asin_cp_map = get_asin_cp_map()
            sku_cp_map = get_sku_cp_map()
            if not asin_cp_map and not sku_cp_map:
                search_cp_keys = None
            else:
                search_cp_keys = set()
                if asin_search_type == "parent_asin":
                    if asin_cp_map:
                        for val in sku_list:
                            search_cp_keys |= asin_cp_map.get(val, set())
                    children = list(
                        LxListingData.objects.filter(parent_asin__in=sku_list)
                        .exclude(asin="")
                        .values_list("seller_sku", "asin")
                        .distinct()
                    )
                    for child_sku, child_asin in children:
                        if child_sku and sku_cp_map:
                            search_cp_keys |= sku_cp_map.get(child_sku, set())
                        if child_asin and asin_cp_map:
                            search_cp_keys |= asin_cp_map.get(child_asin, set())
                else:
                    if sku_cp_map:
                        for val in sku_list:
                            search_cp_keys |= sku_cp_map.get(val, set())
                    if asin_cp_map:
                        related_asins = list(
                            LxListingData.objects.filter(seller_sku__in=sku_list)
                            .exclude(asin="")
                            .values_list("asin", flat=True)
                            .distinct()
                        )
                        for asin_val in related_asins:
                            search_cp_keys |= asin_cp_map.get(asin_val, set())

    date_start = params.get("date_start")
    date_end = params.get("date_end")
    sort_prop = params.get("sort_prop")
    sort_order = params.get("sort_order")

    p_num, p_size = _get_page_params(params)
    all_pairs_list: list[tuple[int, int]] = list(
        qs.values_list("campaign_id", "profile_id").distinct()
    )
    all_pairs_key_set: set[str] = {f"{c}::{p}" for c, p in all_pairs_list}

    for _s in (owner_cp_keys, tag_cp_keys, search_cp_keys):
        if _s is not None:
            if not _s:
                all_pairs_key_set.clear()
                break
            all_pairs_key_set &= _s

    all_pairs_list = [
        (int(c), int(p))
        for cp in all_pairs_key_set
        for c, p in [cp.split("::")]
    ] if all_pairs_key_set else []
    all_pairs_set: set[tuple[str, str]] = {(str(c), str(p)) for c, p in all_pairs_list}
    all_profile_ids: list[int] = sorted({p for _, p in all_pairs_list if p})
    all_campaign_pairs: list[tuple[int, int]] = [(c, p) for c, p in all_pairs_list if c and p]

    # Doris 聚合
    agg_map: dict[str, dict[str, Any]] = {}
    if all_pairs_set:
        doris_qs = LxSpCampaignReport.objects.using("analytics").filter(
            report_date__gte=date_start or "1970-01-01",
            report_date__lte=date_end or "2099-12-31",
        ).values("campaign_id", "profile_id").annotate(
            s_sales=Sum("sales"), s_same_sales=Sum("same_sales"),
            s_orders=Sum("orders"), s_same_orders=Sum("same_orders"),
            s_units=Sum("units"), s_cost=Sum("cost"),
            s_clicks=Sum("clicks"), s_impressions=Sum("impressions"),
        )
        for row in doris_qs:
            cp_key = f"{row['campaign_id']}::{row['profile_id']}"
            if cp_key not in all_pairs_key_set:
                continue
            agg_map[cp_key] = {
                "sales": float(row["s_sales"] or 0),
                "same_sales": float(row["s_same_sales"] or 0),
                "orders": int(row["s_orders"] or 0),
                "same_orders": int(row["s_same_orders"] or 0),
                "units": int(row["s_units"] or 0),
                "cost": float(row["s_cost"] or 0),
                "clicks": int(row["s_clicks"] or 0),
                "impressions": int(row["s_impressions"] or 0),
            }
        for cid_val, pid_val in all_pairs_list:
            cp_key = f"{cid_val}::{pid_val}"
            if cp_key not in agg_map:
                agg_map[cp_key] = {
                    "sales": 0.0, "same_sales": 0.0, "orders": 0,
                    "same_orders": 0, "units": 0, "cost": 0.0,
                    "clicks": 0, "impressions": 0,
                }

    # 排序与分页
    _SORT_METRIC_MAP: dict[str, str] = {
        "impressions": "impressions", "clicks": "clicks", "spends": "cost",
        "cost": "cost", "adsSales": "sales", "sales": "sales",
        "adsOrders": "orders", "orders": "orders", "directSales": "same_sales",
        "directOrders": "same_orders", "adsVolume": "units", "units": "units",
    }
    _SORT_MODEL_MAP: dict[str, str] = {
        "startDate": "start_date", "name": "name", "state": "state",
        "profile_alias": "profile_id",
    }

    reverse = sort_order == "desc"
    metric_key = _SORT_METRIC_MAP.get(sort_prop) if sort_prop else None
    model_key = _SORT_MODEL_MAP.get(sort_prop) if sort_prop else None
    start_idx = (p_num - 1) * p_size
    end_idx = start_idx + p_size

    if model_key:
        order_field = model_key
        if reverse:
            order_field = f"-{order_field}"
        total = len(all_pairs_list)
        if not all_pairs_list:
            items = []
        elif owner_cp_keys is not None or tag_cp_keys is not None or search_cp_keys is not None:
            pair_q = Q()
            for cid, pid in all_pairs_list:
                pair_q |= Q(campaign_id=cid, profile_id=pid)
            items = list(LxSpCampaign.objects.filter(pair_q).order_by(order_field)[start_idx:end_idx].only(
                "id", "campaign_id", "profile_id", "name", "campaign_type",
                "targeting_type", "daily_budget", "start_date", "end_date",
                "state", "serving_status", "bidding", "portfolio_id", "tags",
                "creation_date", "last_updated_date",
            ))
        else:
            items = list(qs.order_by(order_field)[start_idx:end_idx].only(
                "id", "campaign_id", "profile_id", "name", "campaign_type",
                "targeting_type", "daily_budget", "start_date", "end_date",
                "state", "serving_status", "bidding", "portfolio_id", "tags",
                "creation_date", "last_updated_date",
            ))
    else:
        sort_metric = metric_key if metric_key else "impressions"
        sort_reverse = reverse if metric_key else True
        pairs = all_pairs_list
        total = len(pairs)
        pairs.sort(
            key=lambda p: float(
                agg_map.get(f"{p[0]}::{p[1]}", {}).get(sort_metric, 0) or 0
            ),
            reverse=sort_reverse,
        )
        page_pairs = pairs[start_idx:end_idx]
        if not page_pairs:
            items = []
        else:
            pair_q = Q()
            for cid, pid in page_pairs:
                pair_q |= Q(campaign_id=cid, profile_id=pid)
            items = list(LxSpCampaign.objects.filter(pair_q).only(
                "id", "campaign_id", "profile_id", "name", "campaign_type",
                "targeting_type", "daily_budget", "start_date", "end_date",
                "state", "serving_status", "bidding", "portfolio_id", "tags",
                "creation_date", "last_updated_date",
            ))
            pair_order = {f"{c}::{p}": i for i, (c, p) in enumerate(page_pairs)}
            items.sort(key=lambda obj: pair_order.get(
                f"{obj.campaign_id}::{obj.profile_id}", len(page_pairs)
            ))

    # 参考数据
    item_profile_ids = [item.profile_id for item in items if item.profile_id]
    all_profile_info = get_profile_map()
    sid_country = get_sid_country_map()
    profile_map: dict[str, dict[str, str]] = {}
    for pid in item_profile_ids:
        info = all_profile_info.get(str(pid))
        if info:
            c_name = sid_country.get(int(info["sid"] or 0), info["country_code"])
            profile_map[str(pid)] = {
                "profile_alias": info["profile_alias"],
                "country_name": c_name,
                "sid": info["sid"],
            }

    # 广告组合
    portfolio_pairs = [
        (item.portfolio_id, item.profile_id)
        for item in items if item.portfolio_id and item.profile_id
    ]
    portfolio_map: dict[str, str] = {}
    if portfolio_pairs:
        pf_q = Q()
        for pid, pfid in portfolio_pairs:
            pf_q |= Q(portfolio_id=pid, profile_id=pfid)
        for ap in LxAdsPortfolio.objects.filter(pf_q):
            portfolio_map[f"{ap.portfolio_id}::{ap.profile_id}"] = ap.name or str(ap.portfolio_id)

    # 汇率
    _default_ccy: dict[str, Any] = {"icon": "￥", "code": "CNY", "rate": 1.0}
    rate_map_all = get_rate_map()
    all_currency_codes: set[str] = set()
    profile_to_rate_all: dict[str, dict[str, Any]] = {}
    for pid in all_profile_ids:
        info = all_profile_info.get(str(pid))
        cc = info.get("currency_code") if info else None
        profile_to_rate_all[str(pid)] = rate_map_all.get(cc, _default_ccy) if cc else _default_ccy
        if cc:
            all_currency_codes.add(cc)
    if len(all_currency_codes) > 1:
        all_currency_codes.add("USD")
    is_single_currency: bool = len(set(
        rate_map_all.get(c, _default_ccy).get("code", "CNY") for c in all_currency_codes
    )) <= 1
    usd_rate_info = rate_map_all.get("USD", {"rate": 7.2})
    rate_usd_to_cny: float = float(usd_rate_info.get("rate", 7.2))
    ref_currency: dict[str, Any] = (
        rate_map_all.get(next(iter(all_currency_codes)), _default_ccy)
        if is_single_currency and all_currency_codes
        else {"icon": "$", "code": "USD", "rate": rate_usd_to_cny}
    )
    campaign_currency_map: dict[str, dict[str, Any]] = {
        build_campaign_profile_key(item.campaign_id, item.profile_id): profile_to_rate_all.get(
            str(item.profile_id), _default_ccy
        )
        for item in items
    }
    currency_by_campaign_all: dict[str, dict[str, Any]] = {}
    if not is_single_currency:
        currency_by_campaign_all = {
            build_campaign_profile_key(cid, pid): profile_to_rate_all.get(str(pid), _default_ccy)
            for cid, pid in all_campaign_pairs
        }

    # 预算映射
    budget_by_campaign_all: dict[str, float] = {}
    for cid, pid, budget in qs.values_list("campaign_id", "profile_id", "daily_budget"):
        if cid and pid and budget is not None:
            try:
                budget_by_campaign_all[build_campaign_profile_key(cid, pid)] = float(budget)
            except (ValueError, TypeError):
                continue

    # 汇总行 + 指标
    summary = _compute_summary_from_agg(
        agg_map, all_pairs_set, is_single_currency=is_single_currency,
        ref_currency=ref_currency, currency_by_campaign_all=currency_by_campaign_all,
        rate_usd_to_cny=rate_usd_to_cny, budget_by_campaign_all=budget_by_campaign_all,
    )
    meta = summary.pop("_meta", {})
    campaign_pairs = [(str(item.campaign_id), str(item.profile_id)) for item in items if item.campaign_id and item.profile_id]
    metrics_map = _compute_metrics_from_agg(
        agg_map, campaign_pairs, total_clicks_all=meta.get("clicks", 0),
        total_impressions_all=meta.get("impressions", 0),
        total_spends_ref=meta.get("spends_ref", 0.0),
        total_ads_sales_ref=meta.get("ads_sales_ref", 0.0),
        campaign_currency_map=campaign_currency_map,
        is_single_currency=is_single_currency, rate_usd_to_cny=rate_usd_to_cny,
    )

    # 组装响应
    res_list = []
    for item in items:
        dic = _serialize(item)
        p_info = profile_map.get(str(item.profile_id), {})
        dic["profile_alias"] = p_info.get("profile_alias", str(item.profile_id))
        dic["country_name"] = p_info.get("country_name", "-")
        dic["startDate"] = dic.get("start_date")
        dic["budget"] = dic.get("daily_budget")
        raw_type = dic.get("campaign_type", "")
        dic["sponsored_type"] = CAMPAIGN_TYPE_SHORT.get(raw_type, raw_type)
        dic["sponsored_type_raw"] = raw_type
        bidding_val = dic.get("bidding")
        raw_strategy = bidding_val.get("strategy", "") if isinstance(bidding_val, dict) else ""
        dic["bidding_type"] = BIDDING_STRATEGY_LABEL.get(raw_strategy, raw_strategy)
        dic["bidding_type_raw"] = raw_strategy
        if item.portfolio_id and item.profile_id:
            dic["portfolio_name"] = portfolio_map.get(f"{item.portfolio_id}::{item.profile_id}", "")
        else:
            dic["portfolio_name"] = ""
        _ss = resolve_service_status(item.serving_status)
        dic["service_status_label"] = _ss["label"]
        dic["service_status_type"] = _ss["type"]
        dic.update(metrics_map.get(
            build_campaign_profile_key(item.campaign_id, item.profile_id), _empty_metrics()))
        _ccy = campaign_currency_map.get(
            build_campaign_profile_key(item.campaign_id, item.profile_id), {"icon": "$", "code": "USD"})
        dic["currency_icon"] = _ccy.get("icon", "$")
        dic["currency_code"] = _ccy.get("code", "USD")
        dic["store_id"] = p_info.get("sid", "")
        res_list.append(dic)

    # 标签和负责人
    item_keys = [(str(item.campaign_id), str(item.profile_id)) for item in items]
    ad_rows = LxSpAd.objects.filter(build_campaign_profile_query(item_keys)).values("campaign_id", "profile_id", "asin").distinct()
    asin_by_key: dict[str, set[str]] = {}
    for a in ad_rows:
        key = build_campaign_profile_key(a["campaign_id"], a["profile_id"])
        if a["asin"]:
            asin_by_key.setdefault(key, set()).add(a["asin"])
    all_asins = {a for aset in asin_by_key.values() for a in aset}
    asin_label_map: dict[str, list[str]] = {}
    asin_principal_map: dict[str, list[str]] = {}
    if all_asins:
        asin_info = get_asin_info_map()
        all_tag_ids: set[str] = set()
        for asin_val in all_asins:
            info = asin_info.get(asin_val, {})
            tag_ids = info.get("tags", [])
            owners = info.get("owners", [])
            if tag_ids:
                asin_label_map[asin_val] = list(tag_ids)
                all_tag_ids.update(str(t) for t in tag_ids)
            if owners:
                asin_principal_map[asin_val] = list(owners)
        tag_id_to_name: dict[str, str] = {}
        if all_tag_ids:
            for t in LxListingTag.objects.filter(global_tag_id__in=list(all_tag_ids), status="normal").only("global_tag_id", "tag_name"):
                if t.tag_name:
                    tag_id_to_name[t.global_tag_id] = t.tag_name
        for asin_val, values in asin_label_map.items():
            resolved = [tag_id_to_name.get(v, v) for v in values]
            asin_label_map[asin_val] = [v for v in resolved if v]

    # 最近修改信息
    all_adj_map = _build_latest_adjustment_map(items, sid_country)
    state_types = {CampaignExecutionTypeChoices.CAMPAIGN_PAUSE, CampaignExecutionTypeChoices.CAMPAIGN_ENABLE}
    budget_types = {CampaignExecutionTypeChoices.RULE_BUDGET_ADJUSTMENT, CampaignExecutionTypeChoices.MANUAL_BUDGET_ADJUSTMENT}

    for dic in res_list:
        if dic.get("_isSummary"):
            continue
        key = build_campaign_profile_key(dic.get("campaign_id"), dic.get("profile_id"))
        asins = asin_by_key.get(key, set())
        tags_set: set[str] = set()
        for a in asins:
            tags_set.update(asin_label_map.get(a, []))
        dic["tags"] = sorted(tags_set)
        principals_set: set[str] = set()
        for a in asins:
            principals_set.update(asin_principal_map.get(a, []))
        dic["owners"] = sorted(principals_set)
        adj_entry = all_adj_map.get(key)
        if adj_entry and adj_entry.get("_etype") in state_types:
            dic["latest_state_adjustment"] = {"has_recent": True, "lines": adj_entry["lines"]}
            dic["latest_budget_adjustment"] = {"has_recent": False, "lines": []}
        elif adj_entry and adj_entry.get("_etype") in budget_types:
            dic["latest_state_adjustment"] = {"has_recent": False, "lines": []}
            dic["latest_budget_adjustment"] = {"has_recent": True, "lines": adj_entry["lines"]}
        else:
            dic["latest_state_adjustment"] = {"has_recent": False, "lines": []}
            dic["latest_budget_adjustment"] = {"has_recent": False, "lines": []}

    return {
        "total": total, "list": res_list, "summary": summary,
        "pageNum": p_num, "pageSize": p_size,
    }


# ── 内部辅助函数（从 ad_campaign_view 提取）──

def _get_page_params(data: dict) -> tuple[int, int]:
    try:
        p_num = int(data.get("pageNum", 1))
    except (ValueError, TypeError):
        p_num = 1
    try:
        p_size = int(data.get("pageSize", 25))
    except (ValueError, TypeError):
        p_size = 25
    if p_num < 1:
        p_num = 1
    if p_size < 1:
        p_size = 25
    return p_num, p_size


def _serialize(obj: LxSpCampaign) -> dict[str, Any]:
    """序列化单个广告活动为前端字典。"""
    return {
        "id": obj.id, "campaign_id": obj.campaign_id, "profile_id": obj.profile_id,
        "name": obj.name, "campaign_type": obj.campaign_type,
        "targeting_type": obj.targeting_type, "daily_budget": obj.daily_budget,
        "start_date": obj.start_date, "end_date": obj.end_date, "state": obj.state,
        "serving_status": obj.serving_status, "bidding": obj.bidding,
        "portfolio_id": obj.portfolio_id, "tags": obj.tags,
        "creation_date": obj.creation_date, "last_updated_date": obj.last_updated_date,
    }


def _empty_metrics() -> dict[str, Any]:
    """返回空的指标字典。"""
    return {
        "sales": 0.0, "same_sales": 0.0, "orders": 0, "same_orders": 0,
        "units": 0, "cost": 0.0, "clicks": 0, "impressions": 0,
        "acos": 0.0, "roas": 0.0, "ctr": 0.0, "cpc": 0.0,
        "cpa": 0.0, "spends_percent": 0.0, "ads_sales_percent": 0.0,
        "order_conversion_rate": 0.0, "ads_orders_percent": 0.0,
    }


def _compute_metrics_from_agg(agg_map, campaign_pairs, **ctx) -> dict[str, dict[str, Any]]:
    """从聚合数据计算每个 campaign 的指标。"""
    result: dict[str, dict[str, Any]] = {}
    total_clicks_all = float(ctx.get("total_clicks_all", 0) or 0)
    total_impressions_all = float(ctx.get("total_impressions_all", 0) or 0)
    total_spends_ref = float(ctx.get("total_spends_ref", 0) or 0)
    total_ads_sales_ref = float(ctx.get("total_ads_sales_ref", 0) or 0)
    campaign_currency_map = ctx.get("campaign_currency_map", {})
    is_single = ctx.get("is_single_currency", True)
    rate_usd_to_cny = float(ctx.get("rate_usd_to_cny", 7.2))

    for cid, pid in campaign_pairs:
        key = f"{cid}::{pid}"
        agg = agg_map.get(key, {})
        sales = float(agg.get("sales", 0) or 0)
        cost = float(agg.get("cost", 0) or 0)
        clicks = int(agg.get("clicks", 0) or 0)
        impressions = int(agg.get("impressions", 0) or 0)
        orders = int(agg.get("orders", 0) or 0)
        same_sales = float(agg.get("same_sales", 0) or 0)
        same_orders = int(agg.get("same_orders", 0) or 0)
        units = int(agg.get("units", 0) or 0)

        acos = (cost / sales * 100) if sales > 0 else 0.0
        roas = (sales / cost) if cost > 0 else 0.0
        ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
        cpc = (cost / clicks) if clicks > 0 else 0.0
        cpa = (cost / orders) if orders > 0 else 0.0
        spends_pct = (cost / total_spends_ref * 100) if total_spends_ref > 0 else 0.0
        sales_pct = (sales / total_ads_sales_ref * 100) if total_ads_sales_ref > 0 else 0.0
        cvr = (orders / clicks * 100) if clicks > 0 else 0.0
        orders_pct = (orders / total_clicks_all * 100) if total_clicks_all > 0 else 0.0

        result[key] = {
            "sales": sales, "same_sales": same_sales, "orders": orders,
            "same_orders": same_orders, "units": units, "cost": cost,
            "clicks": clicks, "impressions": impressions,
            "acos": round(acos, 2), "roas": round(roas, 2),
            "ctr": round(ctr, 2), "cpc": round(cpc, 2), "cpa": round(cpa, 2),
            "spends_percent": round(spends_pct, 2),
            "ads_sales_percent": round(sales_pct, 2),
            "order_conversion_rate": round(cvr, 2),
            "ads_orders_percent": round(orders_pct, 2),
        }
    return result


def _compute_summary_from_agg(agg_map, all_pairs_set, **ctx) -> dict[str, Any]:
    """计算全量筛选集的汇总指标行。"""
    total_sales = 0.0; total_cost = 0.0; total_clicks = 0; total_impressions = 0
    total_orders = 0; total_same_sales = 0.0; total_same_orders = 0; total_units = 0

    for key, agg in agg_map.items():
        if key not in all_pairs_set:
            continue
        total_sales += float(agg.get("sales", 0) or 0)
        total_cost += float(agg.get("cost", 0) or 0)
        total_clicks += int(agg.get("clicks", 0) or 0)
        total_impressions += int(agg.get("impressions", 0) or 0)
        total_orders += int(agg.get("orders", 0) or 0)
        total_same_sales += float(agg.get("same_sales", 0) or 0)
        total_same_orders += int(agg.get("same_orders", 0) or 0)
        total_units += int(agg.get("units", 0) or 0)

    acos = (total_cost / total_sales * 100) if total_sales > 0 else 0.0
    roas = (total_sales / total_cost) if total_cost > 0 else 0.0
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
    cpc = (total_cost / total_clicks) if total_clicks > 0 else 0.0
    cpa = (total_cost / total_orders) if total_orders > 0 else 0.0

    return {
        "_isSummary": True,
        "sales": total_sales, "same_sales": total_same_sales, "orders": total_orders,
        "same_orders": total_same_orders, "units": total_units, "cost": total_cost,
        "clicks": total_clicks, "impressions": total_impressions,
        "acos": round(acos, 2), "roas": round(roas, 2),
        "ctr": round(ctr, 2), "cpc": round(cpc, 2), "cpa": round(cpa, 2),
        "_meta": {"clicks": total_clicks, "impressions": total_impressions,
                   "spends_ref": total_cost, "ads_sales_ref": total_sales},
    }


def _build_latest_adjustment_map(items, sid_to_country) -> dict[str, dict[str, Any]]:
    """构建每个 campaign 的最近调整信息。"""
    from django.utils import timezone
    from datetime import timedelta
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    from django.db.models import Max
    from apps.ads.sp.rules.models.lx_ad_rule import LxAdRule
    from apps.common.utils.timezone_utils import country_to_timezone

    item_keys = [(item.campaign_id, item.profile_id) for item in items if item.campaign_id and item.profile_id]
    if not item_keys:
        return {}

    threshold = timezone.now() - timedelta(days=7)
    pair_q = Q()
    for cid, pid in item_keys:
        pair_q |= Q(campaign_id=cid, profile_id=pid)
    base_qs = SpCampaignAdjustment.objects.filter(pair_q, created_at__gte=threshold)

    latest = base_qs.values("campaign_id", "profile_id").annotate(max_id=Max("id"))
    id_map = {(r["campaign_id"], r["profile_id"]): r["max_id"] for r in latest if r["max_id"]}
    if not id_map:
        return {}

    records = list(SpCampaignAdjustment.objects.filter(id__in=list(id_map.values())))
    rule_ids = {r.auto_rule_id for r in records if r.auto_rule_id}
    rule_map = {}
    if rule_ids:
        for rule in LxAdRule.objects.filter(id__in=rule_ids).only("id", "name", "condition_sets"):
            rule_map[rule.id] = rule

    result: dict[str, dict[str, Any]] = {}
    for rec in records:
        key = build_campaign_profile_key(rec.campaign_id, rec.profile_id)
        sid = get_profile_map().get(str(rec.profile_id), {}).get("sid", "")
        country_name = sid_to_country.get(int(sid or 0), "")
        tz_name = country_to_timezone(country_name)
        lines = _build_adjustment_lines(rec, rule_map, country_name, tz_name)
        etype = rec.execution_type
        if key not in result:
            result[key] = {"lines": lines, "_etype": etype}
    return result


def _build_adjustment_lines(rec, rule_map, country_name, tz_name) -> list[str]:
    """构建调整记录的可读说明行。"""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    is_rule = bool(rec.auto_rule_id)
    rule = rule_map.get(rec.auto_rule_id) if is_rule else None
    rule_name = getattr(rule, "name", "") if rule else "未知规则"

    if is_rule:
        line1 = f"最近一次修改通过「{rule_name}」规则修改"
    else:
        operator = rec.operator or "未知用户"
        line1 = f"最近一次修改由{operator}完成"

    local_time_str = f"{country_name or '当地'}时间: 未知"
    if rec.created_at:
        try:
            if tz_name:
                tz = ZoneInfo(tz_name)
                local_dt = rec.created_at.astimezone(tz)
                local_time_str = f"{country_name or '当地'}时间: {local_dt.strftime('%Y-%m-%d %H:%M')}"
            else:
                local_time_str = f"{country_name or '当地'}时间: {rec.created_at.strftime('%Y-%m-%d %H:%M')}"
        except (ZoneInfoNotFoundError, Exception):
            pass

    lines = [line1, local_time_str]

    if is_rule and rule:
        try:
            cs = rule.condition_sets
            if isinstance(cs, list) and cs:
                lines.append(f"执行操作: {_summarize_conditions(cs)}")
                lines.append(_summarize_budget_action(
                    getattr(rec, "budget_action", None), rec))
        except Exception:
            pass

    return lines


def _summarize_conditions(condition_sets: Any) -> str:
    """摘要规则条件为字符串。"""
    if not condition_sets or not isinstance(condition_sets, list):
        return "无"
    parts = []
    for cg in condition_sets:
        if not isinstance(cg, dict):
            continue
        days = cg.get("days", "?")
        conds = cg.get("conditions") or []
        if not conds:
            continue
        cond_parts = []
        for c in conds:
            if not isinstance(c, dict):
                continue
            m = c.get("metric") or c.get("field") or "?"
            o = c.get("operator", ">")
            v = c.get("value", "?")
            cond_parts.append(f"{m}{o}{v}")
        if cond_parts:
            parts.append(f"近{days}天: {', '.join(cond_parts)}")
    return "；".join(parts) if parts else "无"


def _summarize_budget_action(budget_action: Any, rec: Any) -> str:
    """摘要预算/状态调整操作。"""
    etype = getattr(rec, "execution_type", None)
    if etype and "PAUSE" in str(etype):
        return "执行操作: 暂停"
    if etype and "ENABLE" in str(etype):
        return "执行操作: 启用"
    if etype and "BUDGET" in str(etype):
        before = getattr(rec, "daily_budget_before", None)
        after = getattr(rec, "daily_budget_after", None)
        if before is not None and after is not None:
            return f"执行操作: 预算 {float(before):.2f} → {float(after):.2f}"
    return "执行操作: 调整"
