"""岗位管理视图。

模块说明：提供岗位的分页、选项、详情、新增、修改、删除以及分配菜单权限接口。
岗位替代原 Role 承载系统菜单权限，与用户的 admin_level 共同构成三轴权限模型。
"""
import logging

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action

from api_v1.models.system.position import Position
from api_v1.models.system.menu import Menu
from api_v1.models.system.user_profile import AdminLevel
from api_v1.serializers.system.position_serializer import (
    PositionSerializer,
    PositionWriteSerializer,
)
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok

logger = logging.getLogger(__name__)


def _is_company_admin(request) -> bool:
    """判断请求者是否为公司管理员或超级用户。

    Args:
        request: DRF Request 对象。

    Returns:
        bool: True 表示有公司管理员权限。
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    try:
        profile = getattr(user, "profile", None)
        return bool(profile and profile.admin_level == AdminLevel.COMPANY_ADMIN)
    except Exception:
        return False


class PositionViewSet(viewsets.ViewSet):
    """岗位管理接口

    路由前缀：/positions
    支持：分页列表、下拉选项、详情表单、新增、修改、删除、分配菜单权限
    """

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        """分页查询岗位列表。

        Query Params:
            keywords (str): 模糊匹配岗位名称或编码。
            status (int): 1=启用，0=禁用。
        """
        qs = Position.objects.all().order_by("order_num", "id")
        kw = request.query_params.get("keywords")
        if kw:
            qs = qs.filter(Q(name__icontains=kw) | Q(code__icontains=kw))
        status = request.query_params.get("status")
        if status is not None:
            try:
                qs = qs.filter(status=bool(int(status)))
            except (ValueError, TypeError):
                pass
        total, items, _, _ = paginate_queryset(request, qs)
        data = PositionSerializer(items, many=True).data
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        """获取岗位下拉选项（轻量，仅返回 id/name）。

        内置岗位（is_builtin=True，如系统管理员）不出现在选项中，
        防止被手动分配给任意用户。
        """
        qs = Position.objects.filter(status=True, is_builtin=False).order_by("order_num", "id")
        return drf_ok([{"label": p.name, "value": p.id} for p in qs])

    @action(detail=False, methods=["get"], url_path=r"(?P<position_id>[^/]+)/form")
    def form(self, request, position_id: str):
        """获取岗位详情（含菜单 ID 列表），用于编辑表单回填。"""
        try:
            position = Position.objects.get(pk=position_id)
        except Position.DoesNotExist:
            return drf_error("未找到岗位", status=404)
        return drf_ok(PositionSerializer(position).data)

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        """GET=完整列表；POST=新建岗位。"""
        if request.method == "GET":
            qs = Position.objects.all().order_by("order_num", "id")
            return drf_ok(PositionSerializer(qs, many=True).data)

        if not _is_company_admin(request):
            return drf_error("仅公司管理员可新建岗位", status=403)
        ser = PositionWriteSerializer(data=request.data)
        if not ser.is_valid():
            return drf_error(str(ser.errors), status=400)
        position = ser.save()
        logger.info("[PositionViewSet] [list_or_create] 新建岗位：%s", position.code)
        return drf_ok(PositionSerializer(position).data, status=201)

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        """PUT=更新单个岗位；DELETE=批量删除（逗号分隔 ID）。"""
        if not _is_company_admin(request):
            return drf_error("仅公司管理员可修改或删除岗位", status=403)
        if request.method == "DELETE":
            id_list = [s.strip() for s in ids.split(",") if s.strip()]
            protected = list(Position.objects.filter(id__in=id_list, is_builtin=True).values_list("code", flat=True))
            if protected:
                return drf_error(f"内置岗位不可删除：{', '.join(protected)}", status=400)
            deleted, _ = Position.objects.filter(id__in=id_list).delete()
            logger.info("[PositionViewSet] [update_or_delete] 删除岗位 IDs=%s，共 %d 条", ids, deleted)
            return drf_ok({"deletedCount": deleted})

        # PUT 单个更新
        try:
            position = Position.objects.get(pk=ids)
        except Position.DoesNotExist:
            return drf_error("未找到岗位", status=404)
        ser = PositionWriteSerializer(position, data=request.data, partial=True)
        if not ser.is_valid():
            return drf_error(str(ser.errors), status=400)
        position = ser.save()
        logger.info("[PositionViewSet] [update_or_delete] 更新岗位：%s", position.code)
        return drf_ok(PositionSerializer(position).data)

    @action(detail=False, methods=["get"], url_path=r"(?P<position_id>[^/]+)/menuIds")
    def menu_ids(self, request, position_id: str):
        """获取岗位已分配的菜单 ID 列表。内置岗位返回全量菜单 ID。"""
        try:
            position = Position.objects.get(pk=position_id)
        except Position.DoesNotExist:
            return drf_error("未找到岗位", status=404)
        if position.is_builtin:
            ids = list(Menu.objects.values_list("id", flat=True))
        else:
            ids = list(position.menus.values_list("id", flat=True))
        return drf_ok(ids)

    @action(detail=False, methods=["put"], url_path=r"(?P<position_id>[^/]+)/menus")
    def update_menus(self, request, position_id: str):
        """覆盖更新岗位的菜单权限（全量替换）。内置岗位权限不可修改。

        Body: {"menuIds": [1, 2, 3]}
        """
        if not _is_company_admin(request):
            return drf_error("仅公司管理员可修改岗位菜单权限", status=403)
        try:
            position = Position.objects.get(pk=position_id)
        except Position.DoesNotExist:
            return drf_error("未找到岗位", status=404)
        if position.is_builtin:
            return drf_error("内置岗位拥有全部权限，不可修改", status=400)
        menu_ids: list[int] = request.data.get("menuIds") or []
        if not isinstance(menu_ids, list):
            return drf_error("menuIds 必须为数组", status=400)
        position.menus.set(Menu.objects.filter(id__in=menu_ids))
        logger.info(
            "[PositionViewSet] [update_menus] 岗位 %s 菜单已更新，共 %d 项",
            position.code,
            len(menu_ids),
        )
        return drf_ok({"menuIds": menu_ids})
