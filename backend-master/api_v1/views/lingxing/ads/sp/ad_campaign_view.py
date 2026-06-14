"""SP 广告活动基础数据视图（LxSpCampaign），仅提供查询。"""
from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db.models import Q, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.models import (
    LxAdsPortfolio,
    LxAdsProfile,
    LxExchangeRate,
    LxListingData,
    LxProductInfo,
    LxShops,
    LxSpAd,
    LxSpCampaign,
    LxSpCampaignReport,
)
from api_v1.serializers.lingxing.ads import LxSpCampaignSerializer
from api_v1.utils.ad_status import resolve_service_status
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok
from api_v1.views.lingxing.ads._helpers import (
    BIDDING_STRATEGY_LABEL,
    CAMPAIGN_TYPE_SHORT,
    build_campaign_profile_key,
    build_campaign_profile_query,
    fmt_money,
    parse_exchange_rate,
)

# Doris 表达式树深度限制为 3000，因此分 batch 查询，每批最多 500 对 (campaign_id, profile_id)。
_DORIS_PAIR_BATCH_SIZE = 500


def _flat_parse_label(raw_label: str) -> list[str]:
    """解析 LxProductInfo.label 字段，将其扁平化为标签字符串列表。

    label 字段存在两种格式：
    1. JSON 数组字符串，如 ``'["清仓", "夏季"]'`` 或 ``'["促销"]'``。
    2. 逗号分隔字符串，如 ``"清仓,夏季"``。

    本函数依次尝试 JSON 解析和逗号分隔解析，确保无论哪种存储格式
    都能正确扁平化为 ``["清仓", "夏季"]``。

    Args:
        raw_label (str): LxProductInfo.label 原始值。

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
            qs = qs.filter(bidding__strategy__in=bidding_strategy.split(","))

        tags = data.get("tags")
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            # LxSpCampaign.tags 为 JSON 数组 [{parent, child}, ...]，
            # 标签值分布在 parent 或 child 字段上
            tag_q = Q()
            for t in tag_list:
                tag_q |= Q(tags__contains=[{"parent": t}])
                tag_q |= Q(tags__contains=[{"child": t}])
            qs = qs.filter(tag_q)

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

        # ── ASIN / MSKU 搜索 ──
        skus = data.get("skus")
        asin_search_type = data.get("asinSearchType", "sku")
        if skus:
            sku_list = [s.strip() for s in skus.split(",") if s.strip()]
            if sku_list:
                listing_filter = Q()
                if asin_search_type == "parent_asin":
                    listing_filter |= Q(sku__in=sku_list)
                    child_skus = list(
                        LxListingData.objects.filter(parent_asin__in=sku_list)
                        .exclude(seller_sku="")
                        .exclude(asin="")
                        .values_list("seller_sku", flat=True)
                        .distinct()
                    )
                    if child_skus:
                        listing_filter |= Q(sku__in=child_skus)
                else:
                    listing_filter |= Q(sku__in=sku_list)
                    related_asins = list(
                        LxListingData.objects.filter(seller_sku__in=sku_list)
                        .exclude(asin="")
                        .values_list("asin", flat=True)
                        .distinct()
                    )
                    if related_asins:
                        listing_filter |= Q(asin__in=related_asins)

                matched_ads = LxSpAd.objects.filter(listing_filter).values(
                    "campaign_id", "profile_id"
                ).distinct()
                campaign_pairs = {(a["campaign_id"], a["profile_id"]) for a in matched_ads}
                if campaign_pairs:
                    pair_q = Q()
                    for cid, pid in campaign_pairs:
                        pair_q |= Q(campaign_id=cid, profile_id=pid)
                    qs = qs.filter(pair_q)

        date_start = data.get("date_start")
        date_end = data.get("date_end")

        # ── 负责人筛选 ──
        owner_ids = data.get("owners")
        if owner_ids:
            owner_id_list = [str(o).strip() for o in owner_ids.split(",") if str(o).strip()]
            if owner_id_list:
                # LxProductInfo.principal_list 为 JSON 数组 [{uid, realname}, ...]
                # 字段名为 uid，不是 principal_uid
                owner_q_parts = Q()
                for uid in owner_id_list:
                    owner_q_parts |= Q(
                        principal_list__contains=[{"uid": int(uid)}]
                    )
                owner_asins = set(
                    LxProductInfo.objects.filter(owner_q_parts)
                    .values_list("asin", flat=True)
                    .distinct()
                )
                if owner_asins:
                    ad_campaign_pairs = set(
                        LxSpAd.objects.filter(asin__in=owner_asins)
                        .values_list("campaign_id", "profile_id")
                        .distinct()
                    )
                    if ad_campaign_pairs:
                        pair_q = Q()
                        for cid, pid in ad_campaign_pairs:
                            pair_q |= Q(campaign_id=cid, profile_id=pid)
                        qs = qs.filter(pair_q)

        sort_prop = data.get("sort_prop")
        sort_order = data.get("sort_order")

        # ── 筛选集全体 campaign / profile 对 ──
        p_num, p_size = self._get_page_params(data)

        # ── 拼接筛选特征参数用于 Redis 缓存键 ──
        cache_key_parts = [
            date_start or "_",
            date_end or "_",
            data.get("keyword") or "_",
            data.get("state") or "_",
            data.get("serving_status") or "_",
            data.get("sponsored_type") or "_",
            data.get("bidding_type") or "_",
            data.get("profiles") or "_",
            data.get("countries") or "_",
            data.get("portfolio_id") or "_",
            data.get("tags") or "_",
            data.get("skus") or "_",
            data.get("asinSearchType") or "_",
        ]
        cache_key = f"sp_campaign_agg:{'|'.join(cache_key_parts)}"

        # ── 先查缓存 ──
        agg_map = cache.get(cache_key)
        all_pairs_list = list(
            qs.values_list("campaign_id", "profile_id").distinct()
        )
        all_pairs_set = {(str(c), str(p)) for c, p in all_pairs_list}
        all_profile_ids = sorted({p for _, p in all_pairs_list if p})
        all_campaign_pairs = [(c, p) for c, p in all_pairs_list if c and p]

        if not isinstance(agg_map, dict):
            # ── 缓存未命中：执行完整聚合查询 ──

            agg_map: dict[str, dict[str, Any]] = {}
            if all_pairs_set:
                # 性能：将笛卡尔积 IN×IN 替换为精确 pair OR 条件，
                # 确保 MySQL 走 (campaign_id, profile_id, report_date) 复合索引。
                # Doris 不支持超 3000 个 OR 节点，也不支持 (a,b) IN (...)
                # 元组语法，因此分 batch 走 OR 查询，每批最多 500 对。
                pairs_sorted = sorted(all_pairs_list)
                for i in range(0, len(pairs_sorted), _DORIS_PAIR_BATCH_SIZE):
                    batch = pairs_sorted[i:i + _DORIS_PAIR_BATCH_SIZE]
                    pair_q = Q()
                    for cid_val, pid_val in batch:
                        pair_q |= Q(campaign_id=cid_val, profile_id=pid_val)

                    agg_qs = LxSpCampaignReport.objects.using("analytics").filter(pair_q)
                    if date_start:
                        agg_qs = agg_qs.filter(report_date__gte=date_start)
                    if date_end:
                        agg_qs = agg_qs.filter(report_date__lte=date_end)

                    agg_qs = agg_qs.values("campaign_id", "profile_id").annotate(
                        s_sales=Sum("sales"),
                        s_same_sales=Sum("same_sales"),
                        s_orders=Sum("orders"),
                        s_same_orders=Sum("same_orders"),
                        s_units=Sum("units"),
                        s_cost=Sum("cost"),
                        s_clicks=Sum("clicks"),
                        s_impressions=Sum("impressions"),
                    )
                    for row in agg_qs:
                        cp_key = f"{row['campaign_id']}::{row['profile_id']}"
                        if cp_key in agg_map:
                            agg_map[cp_key]["sales"] += float(row["s_sales"] or 0)
                            agg_map[cp_key]["same_sales"] += float(row["s_same_sales"] or 0)
                            agg_map[cp_key]["orders"] += int(row["s_orders"] or 0)
                            agg_map[cp_key]["same_orders"] += int(row["s_same_orders"] or 0)
                            agg_map[cp_key]["units"] += int(row["s_units"] or 0)
                            agg_map[cp_key]["cost"] += float(row["s_cost"] or 0)
                            agg_map[cp_key]["clicks"] += int(row["s_clicks"] or 0)
                            agg_map[cp_key]["impressions"] += int(row["s_impressions"] or 0)
                        else:
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
                # 给无数据的 campaign 补齐空值
                for cid_val, pid_val in all_pairs_list:
                    cp_key = f"{cid_val}::{pid_val}"
                    if cp_key not in agg_map:
                        agg_map[cp_key] = {
                            "sales": 0.0, "same_sales": 0.0, "orders": 0,
                            "same_orders": 0, "units": 0, "cost": 0.0,
                            "clicks": 0, "impressions": 0,
                        }
                # 写入缓存
                ttl = 120 if date_start and date_end else 60
                try:
                    cache.set(cache_key, agg_map, ttl)
                except Exception:
                    pass

        # ── 排序（全量数据按指标 / 模型字段排序后再分页）──
        # 排序依赖的指标字段映射：前端 sort_prop → agg_map 内部的 key
        _SORT_METRIC_MAP: dict[str, str] = {
            "impressions": "impressions",
            "clicks": "clicks",
            "spends": "cost",
            "cost": "cost",
            "adsSales": "sales",
            "sales": "sales",
            "adsOrders": "orders",
            "orders": "orders",
            "directSales": "same_sales",
            "directOrders": "same_orders",
            "adsVolume": "units",
            "units": "units",
        }
        # 模型字段映射：前端 sort_prop → LxSpCampaign 真实字段
        _SORT_MODEL_MAP: dict[str, str] = {
            "startDate": "start_date",
            "name": "name",
            "state": "state",
            "profile_alias": "profile_id",
        }

        campaigns = list(
            qs.only(
                "id", "campaign_id", "profile_id", "name", "campaign_type",
                "targeting_type", "daily_budget", "start_date", "end_date",
                "state", "serving_status", "bidding", "portfolio_id", "tags",
                "creation_date", "last_updated_date",
            )
        )
        total = len(campaigns)

        reverse = sort_order == "desc"
        metric_key = _SORT_METRIC_MAP.get(sort_prop) if sort_prop else None
        model_key = _SORT_MODEL_MAP.get(sort_prop) if sort_prop else None

        if metric_key:
            campaigns.sort(
                key=lambda obj: float(
                    agg_map.get(
                        f"{obj.campaign_id}::{obj.profile_id}", {}
                    ).get(metric_key, 0) or 0
                ),
                reverse=reverse,
            )
        elif model_key:
            def _model_sort_key(obj: Any, field: str = model_key) -> Any:
                val = getattr(obj, field, None)
                if val is None:
                    return ""
                return val
            campaigns.sort(key=_model_sort_key, reverse=reverse)
        else:
            # 默认按曝光量降序
            campaigns.sort(
                key=lambda obj: float(
                    agg_map.get(
                        f"{obj.campaign_id}::{obj.profile_id}", {}
                    ).get("impressions", 0) or 0
                ),
                reverse=True,
            )

        start_idx = (p_num - 1) * p_size
        end_idx = start_idx + p_size
        items = campaigns[start_idx:end_idx]

        # ── 店铺与国家数据 ──
        item_profile_ids = [item.profile_id for item in items if item.profile_id]
        profiles_page = list(LxAdsProfile.objects.filter(profile_id__in=item_profile_ids))

        # ── 从 LxShops 拉取国家中文名，不再依赖硬编码 COUNTRY_MAP ──
        all_sids = {sp.sid for sp in profiles_page if sp.sid}
        sid_to_country: dict[int, str] = {}
        if all_sids:
            for shop in LxShops.objects.filter(sid__in=all_sids).only("sid", "country"):
                sid_to_country[shop.sid] = shop.country or ""

        profile_map: dict[str, dict[str, str]] = {}
        for sp in profiles_page:
            country_code = sp.country_code or ""
            c_name = sid_to_country.get(sp.sid, country_code)
            profile_map[str(sp.profile_id)] = {
                "profile_alias": sp.name if sp.name else str(sp.profile_id),
                "country_name": c_name,
                "sid": sp.sid or "",
            }

        # ── 广告组合数据 ──
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

        # ── 汇率体系 ──
        _default_ccy: dict[str, Any] = {"icon": "￥", "code": "CNY", "rate": 1.0}

        all_profiles_in_qs = list(LxAdsProfile.objects.filter(profile_id__in=all_profile_ids))
        all_currency_codes = {p.currency_code for p in all_profiles_in_qs if p.currency_code}

        if len(all_currency_codes) > 1:
            all_currency_codes.add("USD")

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

        profile_to_rate_all: dict[str, dict[str, Any]] = {
            str(p.profile_id): rate_map_all.get(p.currency_code, _default_ccy)
            for p in all_profiles_in_qs
        }

        unique_codes: set[str] = {
            rate_map_all.get(c, _default_ccy).get("code", "CNY")
            for c in all_currency_codes
        }
        is_single_currency: bool = len(unique_codes) <= 1

        usd_rate_info = rate_map_all.get("USD", {"rate": 7.2})
        rate_usd_to_cny: float = float(usd_rate_info.get("rate", 7.2))

        ref_currency: dict[str, Any] = (
            rate_map_all.get(next(iter(all_currency_codes)), _default_ccy)
            if is_single_currency and all_currency_codes
            else {"icon": "$", "code": "USD", "rate": rate_usd_to_cny}
        )

        # 当前分页 campaign → 货币信息
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

        # ── 从 agg_map 计算汇总行 ──
        summary = self._compute_summary_from_agg(
            agg_map, all_pairs_set,
            is_single_currency=is_single_currency,
            ref_currency=ref_currency,
            currency_by_campaign_all=currency_by_campaign_all,
            rate_usd_to_cny=rate_usd_to_cny,
        )
        meta = summary.pop("_meta", {})

        # ── 从 agg_map 计算当前分页指标 ──
        campaign_pairs = [
            (str(item.campaign_id), str(item.profile_id))
            for item in items
            if item.campaign_id and item.profile_id
        ]
        metrics_map = self._compute_metrics_from_agg(
            agg_map, campaign_pairs,
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
                pf_key = f"{item.portfolio_id}::{item.profile_id}"
                dic["portfolio_name"] = portfolio_map.get(pf_key, "")
            else:
                dic["portfolio_name"] = ""

            _ss = resolve_service_status(item.serving_status)
            dic["service_status_label"] = _ss["label"]
            dic["service_status_type"] = _ss["type"]

            dic.update(
                metrics_map.get(
                    build_campaign_profile_key(item.campaign_id, item.profile_id),
                    self._empty_metrics(),
                )
            )

            dic["store_id"] = p_info.get("sid", "")

            res_list.append(dic)

        # ── 标签和负责人数据 ──
        item_keys = [(str(item.campaign_id), str(item.profile_id)) for item in items]
        ad_rows = LxSpAd.objects.filter(
            build_campaign_profile_query(item_keys)
        ).values("campaign_id", "profile_id", "asin").distinct()
        asin_by_key: dict[str, set[str]] = {}
        for a in ad_rows:
            key = build_campaign_profile_key(a["campaign_id"], a["profile_id"])
            if a["asin"]:
                asin_by_key.setdefault(key, set()).add(a["asin"])
        all_asins = {a for aset in asin_by_key.values() for a in aset}
        asin_label_map: dict[str, list[str]] = {}
        asin_principal_map: dict[str, list[str]] = {}
        if all_asins:
            product_rows = LxProductInfo.objects.filter(asin__in=all_asins).values(
                "asin", "label", "principal_list"
            )
            for p in product_rows:
                asin_label_map.setdefault(p["asin"], [])
                asin_principal_map.setdefault(p["asin"], [])
                raw_label = (p["label"] or "").strip()
                if raw_label:
                    # label 字段可能包含 JSON 数组字符串如 '["清仓","夏季"]'，
                    # 也可能是逗号分隔字符串如 "清仓,夏季"，统一解析后扁平化
                    _parsed = _flat_parse_label(raw_label)
                    asin_label_map[p["asin"]].extend(_parsed)
                pl = p["principal_list"]
                if isinstance(pl, list):
                    names = [x.get("realname", "") for x in pl if isinstance(x, dict) and x.get("realname")]
                    asin_principal_map[p["asin"]].extend(names)
        for dic in res_list:
            if dic.get("_isSummary"):
                continue
            key = build_campaign_profile_key(
                dic.get("campaign_id"), dic.get("profile_id")
            )
            asins = asin_by_key.get(key, set())
            tags_set: set[str] = set()
            for a in asins:
                tags_set.update(asin_label_map.get(a, []))
            dic["tags"] = sorted(tags_set)
            principals_set: set[str] = set()
            for a in asins:
                principals_set.update(asin_principal_map.get(a, []))
            dic["owners"] = sorted(principals_set)

        result = {
            "total": total,
            "list": res_list,
            "summary": summary,
            "pageNum": p_num,
            "pageSize": p_size,
        }
        return drf_ok(result)

    @staticmethod
    def _get_page_params(data: dict) -> tuple[int, int]:
        """从请求 data 中解析分页参数。

        Args:
            data (dict): 请求 POST 数据。

        Returns:
            tuple[int, int]: (pageNum, pageSize)。
        """
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
    ) -> dict[str, Any]:
        """从预聚合 agg_map 中计算汇总行与占比基准元数据，零额外数据库查询。

        Args:
            agg_map (dict): campaign 复合键 → 原始聚合值字典。
            all_pairs_set (set[tuple[str, str]]): 有效 (campaign_id, profile_id) 对集合。
            is_single_currency (bool): 是否仅含单一货币。
            ref_currency (dict): 参考货币信息。
            currency_by_campaign_all (dict): campaign → 货币信息映射（多货币时传入）。
            rate_usd_to_cny (float): 美元对人民币汇率。

        Returns:
            dict[str, Any]: 汇总行指标字段，含 _meta 内部基准值。
        """
        icon: str = ref_currency["icon"]

        t_sales = t_same_sales = t_cost = 0.0
        t_orders = t_same_orders = t_units = t_clicks = t_impressions = 0

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

        acos = f"{round(t_cost / t_sales * 100, 2)}%" if t_sales > 0 else "0"
        roas = round(t_sales / t_cost, 2) if t_cost > 0 else 0
        cvr = f"{round(t_orders / t_clicks * 100, 2)}%" if t_clicks > 0 else "0"
        ctr = f"{round(t_clicks / t_impressions * 100, 2)}%" if t_impressions > 0 else "0"
        cpc_raw = round(t_cost / t_clicks, 2) if t_clicks > 0 else 0
        cpa_raw = round(t_cost / t_orders, 2) if t_orders > 0 else 0

        return {
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