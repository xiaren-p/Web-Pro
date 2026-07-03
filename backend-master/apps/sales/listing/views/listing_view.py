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
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated

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
    """SalesProductListingViewSet 视图集。"""
    permission_classes = [IsAuthenticated]
    """销售-商品 Listing 视图。"""

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request: Request) -> Response:
        """获取 Listing 列表分页数据（委托 selector）。"""
        from apps.sales.listing.selectors.listing_page_selector import get_listing_page_data
        result = get_listing_page_data(request.query_params)
        return drf_ok({"total": result["total"], "data": result["data"]})

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
