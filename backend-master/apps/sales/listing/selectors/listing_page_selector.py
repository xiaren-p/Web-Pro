"""Listing 分页查询选择器。

从 ``SalesProductListingViewSet.page`` 提取：查询构建、批量关联数据预取、
数据塑形与格式化等只读逻辑。视图层仅负责请求解析与响应装配。
"""
from typing import Any

from django.db.models import Q
from django.db.models.functions import Cast
from django.db.models import IntegerField

from apps.sales.listing.models.lx_listing_data import LxListingData
from apps.sales.listing.models.lx_listing_tag import LxListingTag
from apps.sales.listing.models.lx_order_profit import LxOrderProfit
from apps.sales.listing.models.lx_listing_meta import LxListingMeta
from apps.lingxing_basic.models.lx_shops import LxShops
from apps.lingxing_basic.models.lx_exchange_rate import LxExchangeRate


def get_listing_page_data(params: dict) -> dict:
    """获取 Listing 分页查询结果，含多维度筛选与数据组装。

    支持国家、店铺、分类、配对状态、上架状态、时间范围、负责人、
    关键词/SKU/ASIN 等筛选，并在后端拼装店铺/元数据/利润数据。

    Args:
        params (dict): DRF request.query_params，需含 pageNum/pageSize。

    Returns:
        dict: ``{total: int, data: list[dict]}``，可直接返回给前端。
    """
    page_num = int(params.get("pageNum", 1))
    page_size = int(params.get("pageSize", 50))
    keyword = params.get("keywords", "")
    search_type = params.get("searchType", "")

    def _get_param_list(key: str) -> list[str]:
        raw = params.getlist(key) or params.getlist(f"{key}[]")
        result: list[str] = []
        for item in raw:
            if "," in item:
                result.extend([x.strip() for x in item.split(",") if x.strip()])
            elif item.strip():
                result.append(item.strip())
        return result

    # 主查询集
    queryset = LxListingData.objects.all()

    # 国家筛选
    countries = [c for c in _get_param_list("country") if c != "__ALL__"]
    if countries:
        queryset = queryset.filter(marketplace__in=countries)

    # 店铺筛选
    shop_ids = [s for s in _get_param_list("shopId") if s != "__ALL__"]
    if shop_ids:
        try:
            int_shop_ids = [int(s) for s in shop_ids]
        except ValueError:
            int_shop_ids = []
        if int_shop_ids:
            queryset = queryset.filter(sid__in=int_shop_ids)

    # 分类筛选
    cat_types = [c for c in _get_param_list("categoryType") if c != "__ALL__"]
    if cat_types:
        meta_q = Q()
        for ct in cat_types:
            if ct == "无":
                meta_q |= Q(assort__isnull=True) | Q(assort="")
            else:
                meta_q |= Q(assort__icontains=ct)
        matched_meta_ids = list(
            LxListingMeta.objects.filter(meta_q).values_list("listing_data_id", flat=True)
        )
        if matched_meta_ids:
            queryset = queryset.filter(id__in=matched_meta_ids)
        else:
            queryset = queryset.none()

    # 配对状态筛选
    pair_status = [p for p in _get_param_list("pairStatus") if p != "__ALL__"]
    if pair_status:
        valid_seller = ~Q(seller_sku__isnull=True) & ~Q(seller_sku="")
        valid_fnsku = ~Q(fnsku__isnull=True) & ~Q(fnsku="")
        if "paired" in pair_status and "unpaired" not in pair_status:
            queryset = queryset.filter(valid_seller & valid_fnsku)
        elif "unpaired" in pair_status and "paired" not in pair_status:
            queryset = queryset.filter(~(valid_seller & valid_fnsku))

    # 上架状态筛选
    listing_status_filters = [s for s in _get_param_list("listingStatus") if s != "__ALL__"]
    has_status_filter = False
    if listing_status_filters:
        status_q = Q()
        for st in listing_status_filters:
            if st == "on":
                status_q |= Q(status=1, is_delete=0)
            if st == "off":
                status_q |= Q(status=0, is_delete=0)
            if st == "deleted":
                status_q |= Q(is_delete=1)
        queryset = queryset.filter(status_q)
        has_status_filter = True
    if not has_status_filter:
        queryset = queryset.filter(is_delete=0)

    # 时间范围筛选
    date_range = _get_param_list("reportUpdatedAt")
    if date_range and len(date_range) >= 2:
        start_date, end_date = date_range[0], date_range[1]
        if start_date and end_date:
            if len(end_date) == 10:
                end_date += " 23:59:59"
            queryset = queryset.filter(
                open_date_display__gte=start_date, open_date_display__lte=end_date
            )

    # 负责人筛选
    owners = [o for o in _get_param_list("owner") if o != "__ALL__"]
    if owners:
        owner_q = Q()
        for owner_uid in owners:
            owner_q |= Q(principal_info__icontains=owner_uid)
        queryset = queryset.filter(owner_q)

    # 关键词搜索
    if keyword:
        keywords_list = [
            k.strip()
            for k in keyword.replace("，", ",").split(",")
            if k.strip()
        ]
        if keywords_list:
            search_q = Q()
            for key in keywords_list:
                if search_type == "seller_sku":
                    search_q |= Q(seller_sku__icontains=key)
                elif search_type == "asin":
                    search_q |= Q(asin__icontains=key)
                elif search_type == "sku":
                    search_q |= Q(local_sku__icontains=key)
                elif search_type == "tag":
                    search_q |= Q(global_tags__icontains=key)
            queryset = queryset.filter(search_q)

    # 排序
    sort_prop = params.get("sort")
    sort_order = params.get("order")
    if sort_prop and sort_order:
        prefix = "" if sort_order == "ascending" else "-"
        if sort_prop == "createTime":
            queryset = queryset.order_by(f"{prefix}open_date_display", "-id")
        elif sort_prop == "msku":
            queryset = queryset.order_by(f"{prefix}seller_sku", "-id")
        elif sort_prop == "skuName":
            queryset = queryset.order_by(f"{prefix}local_sku", f"{prefix}local_name", "-id")
        elif sort_prop == "salesYesterday":
            queryset = queryset.annotate(
                sorted_yesterday_vol=Cast("yesterday_volume", IntegerField())
            ).order_by(f"{prefix}sorted_yesterday_vol", "-id")
        elif sort_prop == "rank":
            queryset = queryset.order_by(f"{prefix}seller_rank", "-id")
        elif sort_prop == "openTime":
            queryset = queryset.order_by(f"{prefix}on_sale_time", "-id")
        elif sort_prop == "firstOrderTime":
            queryset = queryset.order_by(f"{prefix}first_order_time", "-id")
        else:
            queryset = queryset.order_by("-id")
    else:
        queryset = queryset.order_by("-id")

    total = queryset.count()
    page_data = list(queryset[(page_num - 1) * page_size : page_num * page_size])

    # 批量查询关联数据
    listing_ids = [item.id for item in page_data]

    # 利润
    profits = LxOrderProfit.objects.filter(listing_id__in=listing_ids).order_by("-report_date")
    profit_map: dict[int, dict[str, float]] = {}
    for p in profits:
        if p.listing_id not in profit_map:
            profit_map[p.listing_id] = {
                "gross_profit": float(p.gross_profit) if p.gross_profit else 0.0,
                "gross_margin": float(p.gross_margin) if p.gross_margin else 0.0,
            }

    # 店铺
    sid_set = {item.sid for item in page_data}
    shop_map: dict[int, Any] = {}
    for shop in LxShops.objects.filter(sid__in=sid_set):
        shop_map[shop.sid] = shop

    # 元数据
    meta_map: dict[int, Any] = {}
    for meta in LxListingMeta.objects.filter(listing_data_id__in=listing_ids):
        meta_map[meta.listing_data_id] = meta

    # 汇率
    rates_by_code: dict[str, str] = {}
    for r in LxExchangeRate.objects.filter(icon__isnull=False).order_by("-date"):
        if r.code not in rates_by_code and r.icon:
            rates_by_code[r.code] = r.icon

    def _get_icon(currency_code: str) -> str:
        if not currency_code:
            return "$"
        return rates_by_code.get(currency_code, "$")

    def _extract_small_rank(raw: Any) -> int:
        if not raw or not isinstance(raw, list):
            return 0
        min_rank = None
        for item in raw:
            if isinstance(item, dict):
                try:
                    r = int(item.get("rank", 0))
                except (TypeError, ValueError):
                    continue
                if r > 0 and (min_rank is None or r < min_rank):
                    min_rank = r
        return min_rank or 0

    def _normalize_principal_info(raw: Any) -> list[dict[str, Any]]:
        if not raw or not isinstance(raw, list):
            return []
        result: list[dict[str, Any]] = []
        for p_info in raw:
            if isinstance(p_info, dict):
                realname = (
                    p_info.get("realname")
                    or p_info.get("principal_name")
                    or str(p_info.get("principal_uid", ""))
                )
                p_info["realname"] = realname
                p_info["principal_name"] = realname
                result.append(p_info)
        return result

    def _money_display(icon: str, value) -> str:
        if value is None or value == "":
            return ""
        try:
            return f"{icon} {float(value):.2f}"
        except (TypeError, ValueError):
            return ""

    def _percent_display(value) -> str:
        try:
            return f"{round(float(value or 0) * 100, 2)}%"
        except (TypeError, ValueError):
            return "0.00%"

    # 构建 data_list
    data_list: list[dict[str, Any]] = []
    for item in page_data:
        s = shop_map.get(item.sid)
        currency_icon = _get_icon(item.currency_code or "")
        meta = meta_map.get(item.id)

        data_list.append({
            "id": item.id,
            "listing_id": str(item.listing_id or item.id),
            "sid": item.sid,
            "marketplace": item.marketplace or "",
            "shop_name": s.name if s else "",
            "country_code": s.country if s else "",
            "currency_icon": currency_icon,
            "seller_sku": item.seller_sku or "",
            "fnsku": item.fnsku or "",
            "asin": item.asin or "",
            "parent_asin": item.parent_asin or "",
            "small_image_url": item.small_image_url or "",
            "status": item.status if item.status == 1 else 0,
            "is_delete": item.is_delete if item.is_delete == 1 else 0,
            "item_name": item.item_name or "",
            "local_sku": item.local_sku or "",
            "local_name": item.local_name or "",
            "price": float(item.price) if item.price else 0,
            "price_display": _money_display(currency_icon, item.price),
            "landed_price": float(item.landed_price) if item.landed_price else 0,
            "landed_price_display": _money_display(currency_icon, item.landed_price),
            "listing_price": float(item.listing_price) if item.listing_price else 0,
            "listing_price_display": _money_display(currency_icon, item.listing_price),
            "b2b_price": "",
            "b2b_price_display": "",
            "fba_fee": 0,
            "fba_fee_display": "",
            "referral_fee": 0,
            "referral_fee_display": "",
            "yesterday_spend": 0,
            "yesterday_spend_display": "",
            "seven_spend": 0,
            "seven_spend_display": "",
            "fourteen_spend": 0,
            "fourteen_spend_display": "",
            "thirty_spend": 0,
            "thirty_spend_display": "",
            "afn_fulfillable_quantity": item.afn_fulfillable_quantity or 0,
            "yesterday_volume": item.yesterday_volume or "0",
            "total_volume": item.total_volume or "0",
            "fourteen_volume": item.fourteen_volume or "0",
            "thirty_volume": item.thirty_volume or "0",
            "yesterday_amount": item.yesterday_amount or "0.00",
            "yesterday_amount_display": _money_display(currency_icon, item.yesterday_amount),
            "seven_amount": item.seven_amount or "0.00",
            "seven_amount_display": _money_display(currency_icon, item.seven_amount),
            "fourteen_amount": item.fourteen_amount or "0.00",
            "fourteen_amount_display": _money_display(currency_icon, item.fourteen_amount),
            "thirty_amount": item.thirty_amount or "0.00",
            "thirty_amount_display": _money_display(currency_icon, item.thirty_amount),
            "average_seven_volume": item.average_seven_volume or "0.00",
            "average_fourteen_volume": item.average_fourteen_volume or "0.00",
            "average_thirty_volume": item.average_thirty_volume or "0.00",
            "seller_rank": item.seller_rank or 0,
            "small_rank": _extract_small_rank(item.small_rank),
            "seller_category": item.seller_category or "",
            "small_category": "",
            "seller_brand": item.seller_brand or "",
            "principal_info": _normalize_principal_info(item.principal_info),
            "open_date_display": item.open_date_display or "",
            "on_sale_time": item.on_sale_time or "",
            "first_order_time": item.first_order_time or "",
            "assort": meta.assort if meta else "",
            "global_tags": item.global_tags if item.global_tags else [],
            "pair_type": "",
            "amz_product_id": item.listing_id or "",
            "amz_product_id_type": "",
            "variant_text": "",
            "review_num": item.review_num or 0,
            "last_star": item.last_star or "0",
            "fulfillment_channel_type": item.fulfillment_channel_type or "",
            "remarks": meta.remark_text if meta and meta.remark_text else "--",
            "profit_metrics": profit_map.get(item.id, {"gross_profit": 0.0, "gross_margin": 0.0}),
            "gross_profit_display": _money_display(
                currency_icon,
                profit_map.get(item.id, {}).get("gross_profit", 0.0),
            ),
            "gross_margin_display": _percent_display(
                profit_map.get(item.id, {}).get("gross_margin", 0.0)
            ),
        })

    # 标签交叉引用
    _refresh_tags_from_registry(data_list)

    return {"total": total, "data": data_list}


def _refresh_tags_from_registry(data_list: list[dict]) -> None:
    """用 LxListingTag 权威数据刷新 data_list 中的 global_tags。

    以 globalTagId → 最新 tagName / color 覆盖快照值。
    """
    all_tag_ids: set[str] = set()
    for d in data_list:
        tags = d.get("global_tags") or []
        for t in tags:
            if isinstance(t, dict):
                tid = t.get("id") or t.get("globalTagId") or ""
                if tid:
                    all_tag_ids.add(str(tid))
            elif isinstance(t, str) and t:
                all_tag_ids.add(t)

    if not all_tag_ids:
        return

    tag_map: dict[str, dict] = {}
    for item in LxListingTag.objects.filter(global_tag_id__in=list(all_tag_ids), status="normal"):
        if item.tag_name:
            tag_map[item.global_tag_id] = {"tagName": item.tag_name, "color": item.color or ""}

    for d in data_list:
        tags = d.get("global_tags") or []
        if not tags:
            continue
        new_tags = []
        for t in tags:
            if isinstance(t, dict):
                tid = str(t.get("id") or t.get("globalTagId") or "")
                if tid and tid in tag_map:
                    new_tags.append({**t, **tag_map[tid]})
                else:
                    new_tags.append(t)
            elif isinstance(t, str):
                if t in tag_map:
                    new_tags.append({"id": t, **tag_map[t]})
                else:
                    new_tags.append({"id": t, "tagName": t, "color": ""})
        d["global_tags"] = new_tags
