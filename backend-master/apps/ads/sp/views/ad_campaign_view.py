"""SP 广告活动基础数据视图（LxSpCampaign），提供查询与手动预算/状态调整。"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

from django.core.cache import cache as _cache
from django.db.models import Q, Sum
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
_REF_TTL = 600


def _get_profile_map() -> dict[str, dict[str, str]]:
    """profile_id → {profile_alias, country_code, sid} 全量缓存。"""

    _key = "sp_ref_profile_map_v3"
    cached = _cache.get(_key)
    if cached is not None:
        return cached
    result: dict[str, dict[str, str]] = {}
    for p in LxAdsProfile.objects.all().values("profile_id", "name", "country_code", "currency_code", "sid"):
        result[str(p["profile_id"])] = {
            "profile_alias": p["name"] or str(p["profile_id"]),
            "country_code": p["country_code"] or "",
            "currency_code": p["currency_code"] or "",
            "sid": str(p["sid"] or ""),
        }
    _cache.set(_key, result, _REF_TTL)
    return result


def _get_sid_country_map() -> dict[int, str]:
    """sid → 中文国家名 全量缓存。"""

    _key = "sp_ref_sid_country_v2"
    cached = _cache.get(_key)
    if cached is not None:
        return cached
    result: dict[int, str] = {}
    for shop in LxShops.objects.all().only("sid", "country"):
        if shop.sid:
            result[int(shop.sid)] = shop.country or ""
    _cache.set(_key, result, _REF_TTL)
    return result


def _get_rate_map() -> dict[str, dict[str, Any]]:
    """currency_code → {icon, code, rate} 全量缓存（取每币种最新记录）。"""

    _key = "sp_ref_rate_map_v2"
    cached = _cache.get(_key)
    if cached is not None:
        return cached
    result: dict[str, dict[str, Any]] = {}
    for r in LxExchangeRate.objects.all().order_by("-date"):
        if r.code not in result:
            result[r.code] = {
                "icon": r.icon or "￥",
                "code": r.code,
                "rate": parse_exchange_rate(r.my_rate, r.rate_org),
            }
    _cache.set(_key, result, _REF_TTL)
    return result


def _load_all_listing_caches() -> None:
    """一次全表扫描 LxListingData，同时产出 tag/owner/asin_info 三个缓存。

    Celery Beat 280s 刷新保证缓存有效，请求端不应触发重建——
    若缓存已存在则直接返回，仅冷启动时执行一次全表扫描。
    """
    from collections import defaultdict


    # 缓存已全部存在则跳过（Celery Beat 280s 刷新保证大部分请求命中）
    if all(_cache.get(k) for k in (
        "sp_tag_asin_map_v2", "sp_owner_asin_map_v2",
        "sp_asin_tags_map_v2", "sp_asin_owners_map_v2",
        "sp_cp_asin_map_v1", "sp_asin_cp_map_v1", "sp_sku_cp_map_v1",
    )):
        return

    tag_asin: dict[str, set[str]] = defaultdict(set)
    owner_asin: dict[str, set[str]] = defaultdict(set)
    asin_tags: dict[str, list[str]] = defaultdict(list)
    asin_owners: dict[str, list[str]] = defaultdict(list)

    for asin_val, global_tags, principal_info in LxListingData.objects.values_list(
        "asin", "global_tags", "principal_info"
    ):
        # 解析 global_tags
        if isinstance(global_tags, list):
            for entry in global_tags:
                if isinstance(entry, dict):
                    gid = str(entry.get("globalTagId", ""))
                    if gid:
                        tag_asin[gid].add(asin_val)
                        asin_tags[asin_val].append(gid)
        # 解析 principal_info
        if isinstance(principal_info, list):
            for entry in principal_info:
                if isinstance(entry, dict):
                    uid = entry.get("principal_uid")
                    name = entry.get("principal_name", "")
                    if uid is not None:
                        owner_asin[str(uid)].add(asin_val)
                    if name:
                        asin_owners[asin_val].append(name)

    _cache.set_many(
        {
            "sp_tag_asin_map_v2": dict(tag_asin),
            "sp_owner_asin_map_v2": dict(owner_asin),
            "sp_asin_tags_map_v2": dict(asin_tags),
            "sp_asin_owners_map_v2": dict(asin_owners),
        },
        _REF_TTL,
    )

    # 主题：LxSpAd 桥接缓存（聚后筛选用）
    cp_asin: dict[str, set[str]] = defaultdict(set)
    asin_cp: dict[str, set[str]] = defaultdict(set)
    sku_cp: dict[str, set[str]] = defaultdict(set)

    for cid, pid, sku_val, asin_val in LxSpAd.objects.values_list(
        "campaign_id", "profile_id", "sku", "asin"
    ):
        cp_key = f"{cid}::{pid}"
        if asin_val:
            cp_asin[cp_key].add(asin_val)
            asin_cp[asin_val].add(cp_key)
        if sku_val:
            sku_cp[sku_val].add(cp_key)

    _cache.set_many(
        {
            "sp_cp_asin_map_v1": dict(cp_asin),
            "sp_asin_cp_map_v1": dict(asin_cp),
            "sp_sku_cp_map_v1": dict(sku_cp),
        },
        _REF_TTL,
    )



def _get_tag_asin_map() -> dict[str, set[str]]:
    """globalTagId → {asin, ...}。Celery 280s 刷新保证缓存有效，miss 时返回空字典。"""

    return _cache.get("sp_tag_asin_map_v2") or {}


def _get_owner_asin_map() -> dict[str, set[str]]:
    """principal_uid → {asin, ...}。Celery 280s 刷新保证缓存有效，miss 时返回空字典。"""

    return _cache.get("sp_owner_asin_map_v2") or {}


def _get_asin_info_map() -> dict[str, dict[str, list[str]]]:
    """asin → {tags: [globalTagId...], owners: [principal_name...]}。Celery 280s 刷新保证缓存有效。"""

    tags = _cache.get("sp_asin_tags_map_v2") or {}
    owners = _cache.get("sp_asin_owners_map_v2") or {}
    result: dict[str, dict[str, list[str]]] = {}
    for k in tags:
        result[k] = {"tags": tags.get(k, []), "owners": owners.get(k, [])}
    for k in owners:
        if k not in result:
            result[k] = {"tags": tags.get(k, []), "owners": owners.get(k, [])}
    return result


def _get_asin_cp_map() -> dict[str, set[str]]:
    """ASIN → {cp_key, ...} 映射。聚后负责人/标签/MSKU/parent_asin 筛选用。"""

    return _cache.get("sp_asin_cp_map_v1") or {}


def _get_sku_cp_map() -> dict[str, set[str]]:
    """MSKU → {cp_key, ...} 映射。聚后 MSKU 搜索筛选用。"""

    return _cache.get("sp_sku_cp_map_v1") or {}


def _get_cp_asin_map() -> dict[str, set[str]]:
    """cp_key → {asin, ...} 映射。响应中补充 ASIN 字段用。"""

    return _cache.get("sp_cp_asin_map_v1") or {}


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


def _get_operator_name(request: Request) -> str:
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

        # 主题：关键词搜索
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

        # 主题：标签筛选（聚后：计算 cp_key 集，不修改 qs）
        # 链路：tag_name → LxListingTag.global_tag_id → Redis(tagId→ASIN) → asin_cp_map → cp_keys
        tag_cp_keys: set[str] | None = None
        tags = data.get("tags")
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            if tag_list:
                tag_gids = list(LxListingTag.objects.filter(
                    tag_name__in=tag_list, status="normal"
                ).values_list("global_tag_id", flat=True))
                if tag_gids:
                    tag_asin_cache = _get_tag_asin_map()
                    tag_asins: set[str] = set()
                    for gid in tag_gids:
                        gid_str = str(gid)
                        if gid_str and gid_str in tag_asin_cache:
                            tag_asins |= tag_asin_cache[gid_str]
                    if tag_asins:
                        asin_cp_map = _get_asin_cp_map()
                        tag_cp_keys = set()
                        for asin_val in tag_asins:
                            tag_cp_keys |= asin_cp_map.get(asin_val, set())
                    else:
                        tag_cp_keys = set()
                else:
                    tag_cp_keys = set()

        # 主题：负责人筛选（聚后：计算 cp_key 集，不修改 qs）
        # 链路：owner_uid → Redis(uid→ASIN) → asin_cp_map → cp_keys
        owner_cp_keys: set[str] | None = None
        owner_ids = data.get("owners")
        if owner_ids:
            owner_list = [str(o).strip() for o in owner_ids.split(",") if str(o).strip()]
            if owner_list:
                owner_asin_cache = _get_owner_asin_map()
                owner_asins: set[str] = set()
                for uid in owner_list:
                    if uid in owner_asin_cache:
                        owner_asins |= owner_asin_cache[uid]
                if owner_asins:
                    asin_cp_map = _get_asin_cp_map()
                    owner_cp_keys = set()
                    for asin_val in owner_asins:
                        owner_cp_keys |= asin_cp_map.get(asin_val, set())
                else:
                    owner_cp_keys = set()

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

        # 主题：ASIN / MSKU / parent_asin 搜索（聚后：计算 cp_key 集，不修改 qs）
        search_cp_keys: set[str] | None = None
        skus = data.get("skus")
        asin_search_type = data.get("asinSearchType", "sku")
        if skus:
            sku_list = [s.strip() for s in skus.split(",") if s.strip()]
            if sku_list:
                asin_cp_map = _get_asin_cp_map()
                sku_cp_map = _get_sku_cp_map()
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

        date_start = data.get("date_start")
        date_end = data.get("date_end")

        sort_prop = data.get("sort_prop")
        sort_order = data.get("sort_order")

        # 主题：筛选集全体 campaign / profile 对（只含 DB 层筛选：店铺/国家/状态/组合）
        p_num, p_size = self._get_page_params(data)
        all_pairs_list: list[tuple[int, int]] = list(
            qs.values_list("campaign_id", "profile_id").distinct()
        )
        all_pairs_key_set: set[str] = {f"{c}::{p}" for c, p in all_pairs_list}

        # 主题：聚后筛选：owner / tag / 搜索 cp_key 交集
        for _s in (owner_cp_keys, tag_cp_keys, search_cp_keys):
            if _s is not None:
                if not _s:
                    all_pairs_key_set.clear()
                    break
                all_pairs_key_set &= _s
        # 交集后重建列表（空交集 = 无结果）
        all_pairs_list = [
            (int(c), int(p))
            for cp in all_pairs_key_set
            for c, p in [cp.split("::")]
        ] if all_pairs_key_set else []
        all_pairs_set: set[tuple[str, str]] = {(str(c), str(p)) for c, p in all_pairs_list}
        all_profile_ids: list[int] = sorted({p for _, p in all_pairs_list if p})
        all_campaign_pairs: list[tuple[int, int]] = [(c, p) for c, p in all_pairs_list if c and p]

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
            # 给无数据的 campaign 补齐空值
            for cid_val, pid_val in all_pairs_list:
                cp_key = f"{cid_val}::{pid_val}"
                if cp_key not in agg_map:
                    agg_map[cp_key] = {
                        "sales": 0.0, "same_sales": 0.0, "orders": 0,
                        "same_orders": 0, "units": 0, "cost": 0.0,
                        "clicks": 0, "impressions": 0,
                    }

        # 主题：排序与分页（DB 层分页优化：不在内存加载全量 Model 实例）
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
        _SORT_MODEL_MAP: dict[str, str] = {
            "startDate": "start_date",
            "name": "name",
            "state": "state",
            "profile_alias": "profile_id",
        }

        reverse = sort_order == "desc"
        metric_key = _SORT_METRIC_MAP.get(sort_prop) if sort_prop else None
        model_key = _SORT_MODEL_MAP.get(sort_prop) if sort_prop else None

        start_idx = (p_num - 1) * p_size
        end_idx = start_idx + p_size

        if model_key:
            # 路径 A：模型字段排序 → DB 端 ORDER BY + LIMIT，只加载页内 25 条
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
            # 路径 B：指标排序 / 默认排序 → 对筛选后的 all_pairs_list 排序切片
            sort_metric = metric_key if metric_key else "impressions"
            sort_reverse = reverse if metric_key else True  # 默认：曝光量降序

            pairs = all_pairs_list
            total = len(pairs)
            # Python 排序（对轻量元组，比 Model 实例排序快两个数量级）
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
                # 用精确对查询回页内 25 条 Model 实例
                pair_q = Q()
                for cid, pid in page_pairs:
                    pair_q |= Q(campaign_id=cid, profile_id=pid)
                items = list(LxSpCampaign.objects.filter(pair_q).only(
                    "id", "campaign_id", "profile_id", "name", "campaign_type",
                    "targeting_type", "daily_budget", "start_date", "end_date",
                    "state", "serving_status", "bidding", "portfolio_id", "tags",
                    "creation_date", "last_updated_date",
                ))
                # 恢复排序顺序（filter(pair_q) 可能打乱 pairs 的顺序）
                pair_order = {f"{c}::{p}": i for i, (c, p) in enumerate(page_pairs)}
                items.sort(key=lambda obj: pair_order.get(
                    f"{obj.campaign_id}::{obj.profile_id}", len(page_pairs)
                ))

        # 主题：店铺与国家数据（全量缓存，20 分钟刷新）
        item_profile_ids = [item.profile_id for item in items if item.profile_id]
        all_profile_info = _get_profile_map()
        sid_country = _get_sid_country_map()

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
        # 为其他代码可能的引用兜底 key（不在页内但也不影响逻辑）
        sid_to_country: dict[int, str] = sid_country

        # 主题：广告组合数据
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

        # 主题：汇率体系（全量缓存，20 分钟刷新）
        _default_ccy: dict[str, Any] = {"icon": "￥", "code": "CNY", "rate": 1.0}
        rate_map_all = _get_rate_map()

        # 从缓存的 profile 信息中提取全量筛选集的币种集合
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

        # 主题：预算映射：全量筛选集 campaign → daily_budget（供汇总行统计预算，与销售额同口径）
        budget_by_campaign_all: dict[str, float] = {}
        for cid, pid, budget in qs.values_list("campaign_id", "profile_id", "daily_budget"):
            if cid and pid and budget is not None:
                try:
                    budget_by_campaign_all[build_campaign_profile_key(cid, pid)] = float(budget)
                except (ValueError, TypeError):
                    continue

        # 主题：从 agg_map 计算汇总行
        summary = self._compute_summary_from_agg(
            agg_map, all_pairs_set,
            is_single_currency=is_single_currency,
            ref_currency=ref_currency,
            currency_by_campaign_all=currency_by_campaign_all,
            rate_usd_to_cny=rate_usd_to_cny,
            budget_by_campaign_all=budget_by_campaign_all,
        )
        meta = summary.pop("_meta", {})

        # 主题：从 agg_map 计算当前分页指标
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

            # 货币符号 / 代码：取自分页货币映射，供前端预算编辑框显示货币前缀
            _ccy = campaign_currency_map.get(
                build_campaign_profile_key(item.campaign_id, item.profile_id),
                {"icon": "$", "code": "USD"},
            )
            dic["currency_icon"] = _ccy.get("icon", "$")
            dic["currency_code"] = _ccy.get("code", "USD")

            dic["store_id"] = p_info.get("sid", "")

            res_list.append(dic)

        # 主题：最近修改信息（一次查询，按 _etype 拆分为状态和预算两路）
        all_adj_map = self._build_latest_adjustment_map(items, sid_to_country)
        state_types = {CampaignExecutionTypeChoices.CAMPAIGN_PAUSE, CampaignExecutionTypeChoices.CAMPAIGN_ENABLE}
        budget_types = {CampaignExecutionTypeChoices.RULE_BUDGET_ADJUSTMENT, CampaignExecutionTypeChoices.MANUAL_BUDGET_ADJUSTMENT}

        # 主题：标签和负责人数据
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
            asin_info = _get_asin_info_map()
            # 批量查 LxListingTag 把 globalTagId 映射为 tag_name
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
            # 批量查 LxListingTag 把 globalTagId 映射为 tag_name
            tag_id_to_name: dict[str, str] = {}
            if all_tag_ids:
                for t in LxListingTag.objects.filter(
                    global_tag_id__in=list(all_tag_ids), status="normal",
                ).only("global_tag_id", "tag_name"):
                    if t.tag_name:
                        tag_id_to_name[t.global_tag_id] = t.tag_name
            # 把 asin_label_map 中的 globalTagId 字符串替换为 tag_name
            for asin_val, values in asin_label_map.items():
                resolved = [tag_id_to_name.get(v, v) for v in values]
                asin_label_map[asin_val] = [v for v in resolved if v]
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
            # 最近修改信息（星标 + tooltip 文案：拆分为状态和预算两路）
            # 最近修改信息（从合并查询结果中按 _etype 拆分）
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
            operator=_get_operator_name(request),
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
            operator=_get_operator_name(request),
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

        operator = _get_operator_name(request)
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

        operator = _get_operator_name(request)
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
            cached_profiles = _get_profile_map()
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