"""销售-Listing 标签管理 ViewSet。"""
from __future__ import annotations

from typing import Any

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api_v1.models import LxListingTag
from api_v1.utils.responses import drf_error, drf_ok


class ListingTagViewSet(ViewSet):
    """Listing 标签管理视图。"""

    def list(self, request: Request) -> Response:
        """获取标签列表分页数据。"""
        params = request.query_params
        page_num = int(params.get("pageNum", 1))
        page_size = int(params.get("pageSize", 20))

        queryset = LxListingTag.objects.all()

        # 筛选条件
        tag_name = params.get("tagName", "").strip()
        if tag_name:
            queryset = queryset.filter(tag_name__icontains=tag_name)

        tag_type = params.get("type", "").strip()
        if tag_type:
            queryset = queryset.filter(type=tag_type)

        status = params.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        create_by_name = params.get("createByName", "").strip()
        if create_by_name:
            queryset = queryset.filter(create_by_name__icontains=create_by_name)

        # 排序
        sort_prop = params.get("sort")
        sort_order = params.get("order")
        if sort_prop and sort_order:
            prefix = "" if sort_order == "ascending" else "-"
            if sort_prop == "createTime":
                queryset = queryset.order_by(f"{prefix}created_at")
            elif sort_prop == "updateTime":
                queryset = queryset.order_by(f"{prefix}updated_at")
            else:
                queryset = queryset.order_by("-id")
        else:
            queryset = queryset.order_by("-id")

        total = queryset.count()
        page_data = list(queryset[(page_num - 1) * page_size : page_num * page_size])

        data_list: list[dict[str, Any]] = []
        for item in page_data:
            data_list.append({
                "id": item.id,
                "globalTagId": item.global_tag_id or "",
                "tagName": item.tag_name or "",
                "type": item.type or "",
                "color": item.color or "",
                "createByName": item.create_by_name or "",
                "modifyByName": item.modify_by_name or "",
                "status": item.status or "creating",
                "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else "",
                "updateTime": item.updated_at.strftime("%Y-%m-%d %H:%M:%S") if item.updated_at else "",
            })

        return Response({
            "code": 0,
            "message": "success",
            "error_details": [],
            "total": total,
            "data": data_list,
        })

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """获取单个标签详情。"""
        if not pk:
            return drf_error(msg="未提供标签 ID")
        try:
            item = LxListingTag.objects.get(id=int(pk))
        except (ValueError, LxListingTag.DoesNotExist):
            return drf_error(msg="标签不存在")

        return Response({
            "code": 0,
            "message": "success",
            "error_details": [],
            "data": {
                "id": item.id,
                "globalTagId": item.global_tag_id or "",
                "tagName": item.tag_name or "",
                "type": item.type or "",
                "color": item.color or "",
                "createByName": item.create_by_name or "",
                "modifyByName": item.modify_by_name or "",
                "status": item.status or "creating",
                "createTime": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else "",
                "updateTime": item.updated_at.strftime("%Y-%m-%d %H:%M:%S") if item.updated_at else "",
            },
        })

    def create(self, request: Request) -> Response:
        """新增标签。"""
        data = request.data
        tag_name = data.get("tagName", "").strip()
        tag_type = data.get("type", "").strip()
        color = data.get("color", "").strip()

        if not tag_name:
            return drf_error(msg="请输入标签名称")

        # 同名检查：活跃状态标签不允许重名
        active_statuses = ["creating", "normal", "modifying", "deleting"]
        if LxListingTag.objects.filter(tag_name=tag_name, status__in=active_statuses).exists():
            return drf_error(msg=f"标签「{tag_name}」已存在，请勿重复创建")

        operator_name = _get_operator_name(request)

        tag = LxListingTag.objects.create(
            tag_name=tag_name,
            type=tag_type,
            color=color or "#409eff",
            create_by_name=operator_name,
            modify_by_name=operator_name,
            status="creating",
        )
        tag.global_tag_id = f"TAG_{tag.id}"
        tag.save(update_fields=["global_tag_id"])

        return drf_ok(msg="创建成功")

    def update(self, request: Request, pk: str | None = None) -> Response:
        """编辑标签。"""
        if not pk:
            return drf_error(msg="未提供标签 ID")
        try:
            tag = LxListingTag.objects.get(id=int(pk))
        except (ValueError, LxListingTag.DoesNotExist):
            return drf_error(msg="标签不存在")

        data = request.data
        tag_name = data.get("tagName", "").strip()
        color = data.get("color", "").strip()

        has_content_change = False
        if tag_name and tag_name != tag.tag_name:
            # 同名检查
            active_statuses = ["creating", "normal", "modifying", "deleting"]
            if LxListingTag.objects.filter(
                tag_name=tag_name, status__in=active_statuses
            ).exclude(id=tag.id).exists():
                return drf_error(msg=f"标签「{tag_name}」已存在，请勿重复创建")
            tag.tag_name = tag_name
            has_content_change = True
        if color and color != tag.color:
            tag.color = color

        operator_name = _get_operator_name(request)
        tag.modify_by_name = operator_name
        if tag.status not in ["deleting"]:
            tag.status = "modifying" if has_content_change else "normal"

        update_fields = ["color", "modify_by_name", "status"]
        if has_content_change:
            update_fields.append("tag_name")
        tag.save(update_fields=update_fields)
        return drf_ok(msg="更新成功")

    def destroy(self, request: Request, pk: str | None = None) -> Response:
        """删除标签（软删除）。"""
        if not pk:
            return drf_error(msg="未提供标签 ID")
        try:
            tag = LxListingTag.objects.get(id=int(pk))
        except (ValueError, LxListingTag.DoesNotExist):
            return drf_error(msg="标签不存在")

        operator_name = _get_operator_name(request)
        tag.status = "deleting"
        tag.modify_by_name = operator_name
        tag.save(update_fields=["status", "modify_by_name"])
        return drf_ok(msg="删除成功")

    @action(detail=False, methods=["post"], url_path="batch-delete")
    def batch_delete(self, request: Request) -> Response:
        """批量删除标签。"""
        data = request.data
        ids = data.get("ids", [])
        if not ids or not isinstance(ids, list):
            return drf_error(msg="请选择要删除的标签")

        operator_name = _get_operator_name(request)
        tags = LxListingTag.objects.filter(id__in=[int(i) for i in ids if str(i).isdigit()])
        for tag in tags:
            tag.status = "deleting"
            tag.modify_by_name = operator_name
        LxListingTag.objects.bulk_update(tags, ["status", "modify_by_name"])
        return drf_ok(msg="批量删除成功")

    @action(detail=True, methods=["put"], url_path="status")
    def update_status(self, request: Request, pk: str | None = None) -> Response:
        """更新标签状态。"""
        if not pk:
            return drf_error(msg="未提供标签 ID")
        try:
            tag = LxListingTag.objects.get(id=int(pk))
        except (ValueError, LxListingTag.DoesNotExist):
            return drf_error(msg="标签不存在")

        data = request.data
        status = data.get("status", "").strip()
        valid_statuses = [s[0] for s in LxListingTag.STATUS_CHOICES]
        if not status or status not in valid_statuses:
            return drf_error(msg="无效的状态值")

        operator_name = _get_operator_name(request)
        tag.status = status
        tag.modify_by_name = operator_name
        tag.save(update_fields=["status", "modify_by_name"])
        return drf_ok(msg="状态更新成功")

    @action(detail=False, methods=["get"], url_path="type-options")
    def type_options(self, request: Request) -> Response:
        """获取标签类型选项列表。"""
        types = (
            LxListingTag.objects
            .exclude(type="")
            .values_list("type", flat=True)
            .distinct()
            .order_by("type")
        )
        return drf_ok(data=list(types))


def _get_operator_name(request: Request) -> str:
    """获取操作人名称（简化版本，后续可接入用户系统）。"""
    # 优先从 request.user 获取
    user = getattr(request, "user", None)
    if user and hasattr(user, "username") and user.username:
        return str(user.username)
    if user and hasattr(user, "name") and user.name:
        return str(user.name)
    # 降级返回 "admin"
    return "admin"
