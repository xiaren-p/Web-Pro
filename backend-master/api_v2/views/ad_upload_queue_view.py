"""广告上传队列视图（ad_upload_queue_view）。

端点：
  POST   /api/v2/ads/upload/              - 上传 xlsx，解析并创建队列记录
  GET    /api/v2/ads/queue/               - 分页查询队列记录
  DELETE /api/v2/ads/queue/bulk-delete/  - 批量删除队列记录

职责：HTTP 参数解析与响应包装，所有业务逻辑委托 ad_upload_queue_service。
"""

import logging
import json

from django.db.models import Case, IntegerField, Value, When
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from api_v1.auth.bearer_token_auth import BearerTokenAuthentication
from api_v2.models.ad_upload_queue import AdParseStatus, AdUploadQueue
from api_v2.permissions.workflow_permission import IsV2Accessible
from api_v2.serializers.ad_upload_queue_serializer import (
    AdBulkDeleteSerializer,
    AdUploadQueueSerializer,
)
from api_v2.services.ad_upload_queue_service import bulk_delete_queue, parse_and_create_queue

logger = logging.getLogger(__name__)

_AUTH = [BearerTokenAuthentication]
_PERM = [IsV2Accessible]

# 竞价参数字段名与默认值映射
_BIDDING_FIELDS: dict[str, float] = {
    "daily_budget": 1.0,
    "default_bid": 0.12,
    "close_match_bid": 0.12,
    "loose_match_bid": 0.10,
    "substitutes_bid": 0.10,
    "complements_bid": 0.10,
}


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def upload_ad_xlsx(request: Request) -> Response:
    """上传 xlsx 文件，解析后批量创建广告上传队列记录。

    Args:
        request (Request): multipart/form-data，file 字段为 .xlsx 文件。

    Returns:
        Response 201: {"count": N, "list": [...]}
        Response 400: {"detail": "错误描述"}
    """
    file_obj = request.FILES.get("file")
    if not file_obj:
        return Response({"detail": "请上传 file 字段"}, status=status.HTTP_400_BAD_REQUEST)

    if not str(file_obj.name).lower().endswith(".xlsx"):
        return Response({"detail": "仅支持 .xlsx 格式文件"}, status=status.HTTP_400_BAD_REQUEST)

    logger.info(
        "[AdUploadQueueView][upload_ad_xlsx] 开始解析: filename=%s size=%s user=%s",
        file_obj.name, file_obj.size, request.user,
    )

    # 解析广告类型筛选参数（all / auto / manual）
    ad_type_filter: str = request.data.get("ad_type_filter", "all")
    if ad_type_filter not in {"all", "auto", "manual"}:
        ad_type_filter = "all"

    # 解析国家筛选参数（逗号分隔的国家代码字符串，空字符串表示按表需求）
    country_filter_raw: str = request.data.get("country_filter", "")
    country_filter: list[str] | None = (
        [c.strip().upper() for c in country_filter_raw.split(",") if c.strip()]
        if country_filter_raw else None
    )

    # 解析竞价参数（缺失时全部使用字段默认值）
    bidding_params: dict[str, float] = {}
    for field, default in _BIDDING_FIELDS.items():
        raw_val = request.data.get(field)
        if raw_val is not None:
            try:
                bidding_params[field] = float(raw_val)
            except (TypeError, ValueError):
                bidding_params[field] = default

    # 解析按国家预算覆盖（JSON 字符串）
    # 示例：{"PL": 2, "SE": 9}
    daily_budget_by_country: dict[str, float] | None = None
    raw_daily_budget_by_country = request.data.get("daily_budget_by_country")
    if raw_daily_budget_by_country:
        try:
            parsed = json.loads(str(raw_daily_budget_by_country))
            if isinstance(parsed, dict):
                normalized: dict[str, float] = {}
                for key, value in parsed.items():
                    country = str(key).strip().upper()
                    if not country:
                        continue
                    try:
                        numeric_value = float(value)
                    except (TypeError, ValueError):
                        continue
                    if numeric_value > 0:
                        normalized[country] = numeric_value
                if normalized:
                    daily_budget_by_country = normalized
        except (TypeError, ValueError, json.JSONDecodeError):
            daily_budget_by_country = None

    created, error_msg, skipped_warnings = parse_and_create_queue(
        file_obj, request.user, ad_type_filter, country_filter,
        bidding_params if bidding_params else None,
        daily_budget_by_country,
    )

    if error_msg:
        logger.warning(
            "[AdUploadQueueView][upload_ad_xlsx] 解析失败: %s user=%s",
            error_msg, request.user,
        )
        return Response({"detail": error_msg}, status=status.HTTP_400_BAD_REQUEST)

    success_count = sum(1 for r in created if r.parse_status == AdParseStatus.PENDING)
    failed_count = len(created) - success_count
    data = AdUploadQueueSerializer(created, many=True).data
    return Response(
        {
            "count": len(created),
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_warnings": skipped_warnings,
            "list": data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def list_ad_queue(request: Request) -> Response:
    """分页查询广告上传队列记录。

    Query Params:
        page (int): 页码，默认 1。
        page_size (int): 每页条数，默认 20，最大 100。
        parse_status (int): 0=失败 1=队列中 2=成功 3=异常，不传则查全部。
        date_start (str): 创建时间起始日期，格式 YYYY-MM-DD，包含当天。
        date_end (str): 创建时间截止日期，格式 YYYY-MM-DD，包含当天。
        shop (str): 按店铺名模糊过滤。
        country (str): 按国家精确过滤（DE/IT/FR/ES/UK）。

    Returns:
        Response: {"total": N, "page": N, "page_size": N, "list": [...]}
    """
    # 超管或公司管理员可通过 user_id 参数查看其他用户的队列；其余用户强制过滤为自己
    from api_v1.models.system.user_profile import AdminLevel  # noqa: PLC0415
    _profile = getattr(request.user, "profile", None)
    _admin_level = getattr(_profile, "admin_level", None) if _profile else None
    can_view_all: bool = bool(
        request.user.is_superuser or _admin_level == AdminLevel.COMPANY_ADMIN
    )

    user_id_param = request.query_params.get("user_id")
    if can_view_all and user_id_param:
        try:
            qs = AdUploadQueue.objects.filter(
                created_by_id=int(user_id_param)
            ).select_related("created_by")
        except (ValueError, TypeError):
            qs = AdUploadQueue.objects.filter(created_by=request.user).select_related("created_by")
    else:
        qs = AdUploadQueue.objects.filter(created_by=request.user).select_related("created_by")

    parse_status_param = request.query_params.get("parse_status")
    if parse_status_param is not None:
        try:
            qs = qs.filter(parse_status=int(parse_status_param))
        except ValueError:
            pass

    date_start_param = request.query_params.get("date_start")
    if date_start_param:
        qs = qs.filter(created_at__date__gte=date_start_param)

    date_end_param = request.query_params.get("date_end")
    if date_end_param:
        qs = qs.filter(created_at__date__lte=date_end_param)

    shop_param = request.query_params.get("shop")
    if shop_param:
        qs = qs.filter(shop__icontains=shop_param)

    country_param = request.query_params.get("country")
    if country_param:
        qs = qs.filter(country=country_param)

    # 固定排序：队列中（parse_status=1）始终置顶，其余按创建时间倒序。
    # 该排序在后端完成，确保分页场景下排序稳定一致。
    qs = qs.annotate(
        status_priority=Case(
            When(parse_status=AdParseStatus.PENDING, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("status_priority", "-created_at", "-id")

    try:
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    except ValueError:
        page, page_size = 1, 20

    total = qs.count()
    offset = (page - 1) * page_size
    records = qs[offset: offset + page_size]

    data = AdUploadQueueSerializer(records, many=True).data
    return Response({"total": total, "page": page, "page_size": page_size, "list": data})


@api_view(["DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def bulk_delete_ad_queue(request: Request) -> Response:
    """批量删除广告上传队列记录。

    Args:
        request (Request): JSON body {"ids": [1, 2, 3]}

    Returns:
        Response: {"deleted_count": N}
        Response 400: 参数校验错误详情
    """
    serializer = AdBulkDeleteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    deleted_count = bulk_delete_queue(
        serializer.validated_data["ids"],
        request.user,
    )
    return Response({"deleted_count": deleted_count})


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_PERM)
def retry_ad_queue(request: Request) -> Response:
    """将失败（parse_status=0）的队列记录重置为待提交（parse_status=1，队列中）。

    Args:
        request (Request): JSON body {"ids": [1, 2, 3]}

    Returns:
        Response: {"retried_count": N}
        Response 400: ids 为空或非法
    """
    ids = request.data.get("ids", [])
    if not ids or not isinstance(ids, list):
        return Response({"detail": "ids 不能为空"}, status=status.HTTP_400_BAD_REQUEST)

    logger.info(
        "[AdUploadQueueView][retry_ad_queue] 重试队列记录: ids=%s user=%s",
        ids, request.user,
    )

    # FAILED 和 ANOMALY 均可重试；不清除已落库的 campaign_id / ad_group_id 等 ID，
    # 由 _submit_single 按"跳过已完成步骤"逻辑从断点续跑。
    # 权限与列表页保持一致：超管/公司管理员可操作所有记录，其余用户仅可操作自己记录。
    from api_v1.models.system.user_profile import AdminLevel  # noqa: PLC0415

    profile = getattr(request.user, "profile", None)
    admin_level = getattr(profile, "admin_level", None) if profile else None
    can_retry_all = bool(
        request.user.is_superuser or admin_level == AdminLevel.COMPANY_ADMIN
    )

    queryset = AdUploadQueue.objects.filter(
        id__in=ids,
        parse_status__in=[AdParseStatus.FAILED, AdParseStatus.ANOMALY],
    )
    if not can_retry_all:
        queryset = queryset.filter(created_by=request.user)

    retried_count = queryset.update(parse_status=AdParseStatus.PENDING, msg="队列中")

    return Response({"retried_count": retried_count})
