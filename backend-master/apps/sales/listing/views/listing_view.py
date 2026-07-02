"""销售-商品 Listing ViewSet。

承载 Listing 的分页查询与标签/分类/备注的批量 upsert 接口。
所有数据形态加工（货币符号映射、principal_info 字段补齐、状态码二值化等）
均在后端定型，前端拿到字段直接渲染。

自 LxListingInfo 迁移至 LxListingData 后，主查询集不再依赖 select_related，
关联数据（店铺、元数据、利润）改为手动批量查询拼装。
"""
from __future__ import annotations

from typing import Any

from django.db.models import IntegerField, Q
from django.db.models.functions import Cast
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.sales.models.lx_shops import LxShops
from apps.sales.models.lx_exchange_rate import LxExchangeRate
from apps.sales.listing.models.lx_listing_data import LxListingData
from apps.sales.listing.models.lx_listing_meta import LxListingMeta
from apps.sales.listing.models.lx_listing_tag import LxListingTag
from apps.sales.listing.models.lx_order_profit import LxOrderProfit
from apps.common.utils.responses import drf_error, drf_ok
from apps.sales.listing.models.listing_tag_modify_queue import (
    ListingTagModifyQueue,
    ModifyActionChoices,
)


def _refresh_tags_from_registry(data_list: list[dict[str, Any]]) -> None:
    """用 LxListingTag 表中的权威数据覆盖 data_list 中 global_tags 的 tagName/color。

    仅在 globalTagId 非空且存在匹配记录时覆盖；无匹配则保留快照原值。
    """
    if not data_list:
        return

    all_tag_ids: set[str] = set()
    for item_data in data_list:
        for tag in item_data.get("global_tags", []):
            if isinstance(tag, dict):
                gid = tag.get("globalTagId", "") or ""
                if gid:
                    all_tag_ids.add(gid)

    if not all_tag_ids:
        return

    tag_map: dict[str, dict[str, str]] = {}
    for t in LxListingTag.objects.filter(global_tag_id__in=all_tag_ids, status="normal"):
        tag_map[t.global_tag_id] = {
            "globalTagId": t.global_tag_id or "",
            "tagName": t.tag_name or "",
            "color": t.color or "",
        }

    for item_data in data_list:
        refreshed: list[dict[str, str]] = []
        for tag in item_data.get("global_tags", []):
            if not isinstance(tag, dict):
                continue
            gid = tag.get("globalTagId", "") or ""
            if gid and gid in tag_map:
                refreshed.append(tag_map[gid])
            else:
                refreshed.append({
                    "globalTagId": tag.get("globalTagId", ""),
                    "tagName": tag.get("tagName", ""),
                    "color": tag.get("color", ""),
                })
        item_data["global_tags"] = refreshed


class SalesProductListingViewSet(ViewSet):
    """销售-商品 Listing 视图。"""

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request: Request) -> Response:
        """获取 Listing 列表分页数据。

        支持多维筛选（国家、店铺、配对状态、上架状态、负责人、关键字 / SKU / ASIN
        等），并将店铺/元数据/利润数据在后端拼装为前端可直接渲染的扁平结构。
        """
        params = request.query_params
        page_num = int(params.get("pageNum", 1))
        page_size = int(params.get("pageSize", 50))

        keyword = params.get("keywords", "")
        search_type = params.get("searchType", "")

        def get_param_list(key: str) -> list[str]:
            """从 query_params 中读取多值参数，兼容 ``key=a,b`` 与 ``key[]=a&key[]=b``。"""
            raw = params.getlist(key) or params.getlist(f"{key}[]")
            result: list[str] = []
            for item in raw:
                if "," in item:
                    result.extend([x.strip() for x in item.split(",") if x.strip()])
                elif item.strip():
                    result.append(item.strip())
            return result

        # 主查询集：LxListingData 替代 LxListingInfo
        queryset = LxListingData.objects.all()

        # 国家筛选：直接使用 LxListingData.marketplace
        countries = [c for c in get_param_list("country") if c != "__ALL__"]
        if countries:
            queryset = queryset.filter(marketplace__in=countries)

        # 店铺筛选：直接使用 LxListingData.sid
        shop_ids = [s for s in get_param_list("shopId") if s != "__ALL__"]
        if shop_ids:
            try:
                int_shop_ids = [int(s) for s in shop_ids]
            except ValueError:
                int_shop_ids = []
            if int_shop_ids:
                queryset = queryset.filter(sid__in=int_shop_ids)

        # 分类筛选：通过 LxListingMeta.assort 间接过滤
        cat_types = [c for c in get_param_list("categoryType") if c != "__ALL__"]
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
        pair_status = [p for p in get_param_list("pairStatus") if p != "__ALL__"]
        if pair_status:
            valid_seller = ~Q(seller_sku__isnull=True) & ~Q(seller_sku="")
            valid_fnsku = ~Q(fnsku__isnull=True) & ~Q(fnsku="")
            if "paired" in pair_status and "unpaired" not in pair_status:
                queryset = queryset.filter(valid_seller & valid_fnsku)
            elif "unpaired" in pair_status and "paired" not in pair_status:
                queryset = queryset.filter(~(valid_seller & valid_fnsku))

        # 上架状态筛选：status (0/1) + is_delete (0/1) 替代旧的三分法
        listing_status_filters = [
            s for s in get_param_list("listingStatus") if s != "__ALL__"
        ]
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
        date_range = get_param_list("reportUpdatedAt")
        if date_range and len(date_range) >= 2:
            start_date, end_date = date_range[0], date_range[1]
            if start_date and end_date:
                if len(end_date) == 10:
                    end_date += " 23:59:59"
                queryset = queryset.filter(
                    open_date_display__gte=start_date, open_date_display__lte=end_date
                )

        # 负责人筛选：直接使用 LxListingData.principal_info (JSONField)
        owners = [o for o in get_param_list("owner") if o != "__ALL__"]
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
                queryset = queryset.order_by(
                    f"{prefix}local_sku",
                    f"{prefix}local_name",
                    "-id",
                )
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

        # ── 手动批量查询关联数据 ──

        listing_ids = [item.id for item in page_data]

        # 利润数据：按 listing_id 聚合（取最新一条）
        profits = LxOrderProfit.objects.filter(
            listing_id__in=listing_ids
        ).order_by("-report_date")
        profit_map: dict[int, dict[str, float]] = {}
        for p in profits:
            if p.listing_id not in profit_map:
                profit_map[p.listing_id] = {
                    "gross_profit": float(p.gross_profit) if p.gross_profit else 0.0,
                    "gross_margin": float(p.gross_margin) if p.gross_margin else 0.0,
                }

        # 店铺数据：按 sid 集合批量查询
        sid_set = {item.sid for item in page_data}
        shop_map: dict[int, Any] = {}
        for shop in LxShops.objects.filter(sid__in=sid_set):
            shop_map[shop.sid] = shop

        # 元数据：按 listing_data_id 集合批量查询 LxListingMeta
        meta_map: dict[int, Any] = {}
        for meta in LxListingMeta.objects.filter(listing_data_id__in=listing_ids):
            meta_map[meta.listing_data_id] = meta

        # 货币符号映射：直接从 LxListingData.currency_code → LxExchangeRate.icon
        rates_by_code: dict[str, str] = {}
        for r in LxExchangeRate.objects.filter(icon__isnull=False).order_by("-date"):
            if r.code not in rates_by_code and r.icon:
                rates_by_code[r.code] = r.icon

        def _get_icon(currency_code: str) -> str:
            """根据币种代码获取货币符号，默认返回 '$'。"""
            if not currency_code:
                return "$"
            return rates_by_code.get(currency_code, "$")

        def _extract_small_rank(raw: Any) -> int:
            """从 LxListingData.small_rank（JSON 数组）中提取最小排名整数值。

            small_rank 格式：[{"category": "...", "rank": 123}, ...]
            取 rank 最小的那个，若为空或解析失败返回 0。
            """
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
            """标准化 principal_info，补齐 realname 字段供前端直接展示。

            LxListingData.principal_info 格式：
            [{"principal_uid": "...", "principal_name": "..."}, ...]
            """
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

        # ── 金额与百分比格式化辅助函数 ──

        def _money_display(icon: str, value) -> str:
            """金额定型字符串：``"$ 12.34"`` 形式，None/空返回空串。"""
            if value is None or value == "":
                return ""
            try:
                return f"{icon} {float(value):.2f}"
            except (TypeError, ValueError):
                return ""

        def _percent_display(value) -> str:
            """百分比定型字符串：``"12.34%"``，None 返回 ``"0.00%"``。"""
            try:
                return f"{round(float(value or 0) * 100, 2)}%"
            except (TypeError, ValueError):
                return "0.00%"

        # ── 构建 data_list ──

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
                # LxShops 没有 country_code 字段，用 country 替代
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
                # 价格（CharField → float）
                "price": float(item.price) if item.price else 0,
                "price_display": _money_display(currency_icon, item.price),
                "landed_price": float(item.landed_price) if item.landed_price else 0,
                "landed_price_display": _money_display(currency_icon, item.landed_price),
                "listing_price": float(item.listing_price) if item.listing_price else 0,
                "listing_price_display": _money_display(currency_icon, item.listing_price),
                # TODO: b2b_price 在 LxListingData 中不存在，暂时留空
                "b2b_price": "",
                "b2b_price_display": "",
                # TODO: fba_fee / referral_fee 在 LxListingData 中不存在，暂时留空
                "fba_fee": 0,
                "fba_fee_display": "",
                "referral_fee": 0,
                "referral_fee_display": "",
                # TODO: *_spend 系列在 LxListingData 中不存在，暂时留空
                "yesterday_spend": 0,
                "yesterday_spend_display": "",
                "seven_spend": 0,
                "seven_spend_display": "",
                "fourteen_spend": 0,
                "fourteen_spend_display": "",
                "thirty_spend": 0,
                "thirty_spend_display": "",
                # 库存
                "afn_fulfillable_quantity": item.afn_fulfillable_quantity or 0,
                # 销量 / 销售额（CharField → 字符串，保持原输出类型）
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
                # 排名 / 类目
                "seller_rank": item.seller_rank or 0,
                "small_rank": _extract_small_rank(item.small_rank),
                "seller_category": item.seller_category or "",
                # LxListingData 无 small_category 字段，暂时留空
                "small_category": "",
                "seller_brand": item.seller_brand or "",
                # 负责人
                "principal_info": _normalize_principal_info(item.principal_info),
                # 时间
                "open_date_display": item.open_date_display or "",
                "on_sale_time": item.on_sale_time or "",
                "first_order_time": item.first_order_time or "",
                # 分类与标签（来源变更）
                "assort": meta.assort if meta else "",
                "global_tags": item.global_tags if item.global_tags else [],
                # 以下字段 LxListingData 中不存在，暂时留空
                # TODO: pair_type 待后续确认来源
                "pair_type": "",
                "amz_product_id": item.listing_id or "",
                # TODO: amz_product_id_type 待后续确认来源
                "amz_product_id_type": "",
                # TODO: variant_text 待后续确认来源
                "variant_text": "",
                # 评论 / 评分
                "review_num": item.review_num or 0,
                "last_star": item.last_star or "0",
                "fulfillment_channel_type": item.fulfillment_channel_type or "",
                # 备注（来源改为 LxListingMeta）
                "remarks": meta.remark_text if meta and meta.remark_text else "--",
                # 利润
                "profit_metrics": profit_map.get(
                    item.id, {"gross_profit": 0.0, "gross_margin": 0.0}
                ),
                "gross_profit_display": _money_display(
                    currency_icon,
                    profit_map.get(item.id, {}).get("gross_profit", 0.0),
                ),
                "gross_margin_display": _percent_display(
                    profit_map.get(item.id, {}).get("gross_margin", 0.0)
                ),
            })

        # 全局标签交叉引用：用 LxListingTag 中权威数据（最新 tagName / color）覆盖快照值
        _refresh_tags_from_registry(data_list)

        return Response({
            "code": 0,
            "message": "success",
            "error_details": [],
            "total": total,
            "data": data_list,
        })

    @action(detail=False, methods=["post"], url_path="labels/upsert")
    def upsert_labels(self, request: Request) -> Response:
        """批量更新全局标签（``LxListingData.global_tags``）。

        global_tags 为 JSON 数组，前端提交的格式：
        [{"id": 12345, "asin": "xxx", "tags": [...]}, ...]
        id 为主键（LxListingData.id），用于精确匹配单条记录。

        写入 LxListingData.global_tags 后，自动计算新旧差异并写入
        ListingTagModifyQueue 队列，供异步任务消费。
        """
        data = request.data
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return drf_error(msg="参数格式错误")

        # 用主键 id 精确匹配，避免一个 asin 对应多条记录
        ids = [item.get("id") for item in data if item.get("id")]
        if not ids:
            return drf_ok(msg="未提供任何记录 ID")

        records = list(LxListingData.objects.filter(id__in=ids))
        record_map: dict[int, LxListingData] = {r.id: r for r in records}

        queue_entries: list[ListingTagModifyQueue] = []
        updates: list[LxListingData] = []

        for item in data:
            record_id = item.get("id")
            if not record_id:
                continue
            record = record_map.get(record_id)
            if not record:
                continue

            tags = item.get("tags", [])
            normalized_tags: list[dict[str, Any]] = []
            for t in tags if isinstance(tags, list) else []:
                if isinstance(t, dict):
                    normalized_tags.append({
                        "globalTagId": t.get("globalTagId", ""),
                        "tagName": t.get("tagName", ""),
                        "color": t.get("color", ""),
                    })

            new_ids = {t["globalTagId"] for t in normalized_tags if t["globalTagId"]}

            old_tags: list[dict[str, Any]] = record.global_tags or []
            old_ids = {t.get("globalTagId", "") for t in old_tags if t.get("globalTagId")}

            added_ids = new_ids - old_ids
            removed_ids = old_ids - new_ids

            msku = record.seller_sku or ""
            sid = record.sid or 0

            if added_ids:
                queue_entries.append(ListingTagModifyQueue(
                    action=ModifyActionChoices.ADD,
                    msku=msku,
                    sid=sid,
                    tag_ids=list(added_ids),
                ))

            if removed_ids:
                queue_entries.append(ListingTagModifyQueue(
                    action=ModifyActionChoices.REMOVE,
                    msku=msku,
                    sid=sid,
                    tag_ids=list(removed_ids),
                ))

            record.global_tags = normalized_tags
            updates.append(record)

        if updates:
            LxListingData.objects.bulk_update(updates, ["global_tags"])

        if queue_entries:
            ListingTagModifyQueue.objects.bulk_create(queue_entries)

        return drf_ok(msg="标签保存成功")

    @action(detail=False, methods=["post"], url_path="assort/upsert")
    def upsert_assort(self, request: Request) -> Response:
        """批量更新或新增分类（``LxListingMeta.assort``）。

        通过 id（LxListingData 主键）精确匹配。
        """
        data = request.data
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return drf_error(msg="参数格式错误")

        ids = [item.get("id") for item in data if item.get("id")]
        if not ids:
            return drf_ok(msg="未提供任何记录 ID")

        target_ids = [int(i) for i in ids]
        existing_metas = LxListingMeta.objects.filter(listing_data_id__in=target_ids)
        meta_map: dict[int, Any] = {m.listing_data_id: m for m in existing_metas}

        update_metas: list[LxListingMeta] = []
        create_metas: list[LxListingMeta] = []
        for item in data:
            record_id = item.get("id")
            if not record_id:
                continue
            try:
                data_id = int(record_id)
            except (TypeError, ValueError):
                continue
            assort = item.get("assort", "")

            if data_id in meta_map:
                meta = meta_map[data_id]
                meta.assort = assort
                update_metas.append(meta)
            else:
                create_metas.append(
                    LxListingMeta(listing_data_id=data_id, assort=assort)
                )

        if update_metas:
            LxListingMeta.objects.bulk_update(update_metas, ["assort", "updated_at"])
        if create_metas:
            LxListingMeta.objects.bulk_create(create_metas)

        return drf_ok(msg="分类保存成功")

    @action(detail=False, methods=["post"], url_path="remark/upsert")
    def upsert_remark(self, request: Request) -> Response:
        """新增或更新单条 Listing 备注（``LxListingMeta.remark_text``）。"""
        data = request.data
        listing_id = data.get("listing_id")
        remark_text = data.get("remark", "")

        if not listing_id:
            return drf_error(msg="未提供 listing_id")

        try:
            listing_id_int = int(listing_id)
        except (TypeError, ValueError):
            return drf_error(msg="listing_id 格式错误")

        # 确认 LxListingData 存在
        if not LxListingData.objects.filter(id=listing_id_int).exists():
            return drf_error(msg="Listing 不存在")

        LxListingMeta.objects.update_or_create(
            listing_data_id=listing_id_int,
            defaults={"remark_text": remark_text},
        )
        return drf_ok(msg="备注保存成功")
