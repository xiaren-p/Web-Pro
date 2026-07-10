"""刊登模板视图。

提供模板的 CRUD 接口，路由前缀：api/v1/sales/publication/templates。

列表（不含 data_json）、详情（含 data_json）、新增、编辑、软删除。
前端发送 amazon_data，后端映射到 data_json 存储。
"""
import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.common.utils.pagination import paginate_queryset
from apps.common.utils.responses import drf_error, drf_ok
from apps.sales.publication.selectors.publish_template_selector import (
    get_template_page_qs,
    get_template_detail,
)
from apps.sales.publication.serializers.publish_template_serializer import (
    PublishTemplateListSerializer,
    PublishTemplateDetailSerializer,
    PublishTemplateWriteSerializer,
)

logger = logging.getLogger(__name__)


class PublishTemplateViewSet(viewsets.ViewSet):
    """刊登模板 CRUD 接口。

    路由前缀：/sales/publication/templates
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        """分页查询模板列表（不含 data_json）。

        Query params:
            pageNum: 页码（默认 1）。
            pageSize: 每页条数（默认 20）。
            keyword: 模板名称模糊搜索关键词。

        Returns:
            ``{total, list}``，list 中每项为 PublishTemplateListSerializer 输出。
        """
        keyword = request.query_params.get("keyword", "").strip()
        qs = get_template_page_qs(keyword=keyword or None)
        total, items, _, _ = paginate_queryset(request, qs)
        return drf_ok({
            "total": total,
            "list": PublishTemplateListSerializer(items, many=True).data,
        })

    @action(detail=False, methods=["get"], url_path=r"(?P<pk>[^/]+)/form")
    def form(self, request, pk: str):
        """获取模板详情（含 data_json），用于编辑表单回填。

        Args:
            pk: 模板主键 ID。

        Returns:
            PublishTemplateDetailSerializer 输出，含 dataJson 字段。
        """
        template = get_template_detail(pk)
        if template is None:
            return drf_error("未找到模板", status=404)
        return drf_ok(PublishTemplateDetailSerializer(template).data)

    @action(detail=False, methods=["post"], url_path="")
    def create_template(self, request):
        """新增模板。

        Body:
            templateName: 模板名称。
            marketplaceId: Amazon 市场 ID。
            productType: 商品类型（如 SHIRT）。
            productTypeUniqueId: 商品类型唯一 ID。
            amazonData: 动态 Amazon 属性数据（映射到 data_json）。

        Returns:
            创建后的模板详情。
        """
        ser = PublishTemplateWriteSerializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            return drf_error(str(ser.errors), status=400)
        template = ser.save()
        logger.info(
            "[PublishTemplateViewSet] [create_template] 新建模板：%s (id=%s)",
            template.template_name,
            template.id,
        )
        return drf_ok(PublishTemplateDetailSerializer(template).data, status=201)

    @action(detail=False, methods=["put"], url_path=r"(?P<pk>[^/]+)")
    def update_template(self, request, pk: str):
        """编辑模板。

        Args:
            pk: 模板主键 ID。

        Body:
            templateName / marketplaceId / productType / amazonData 等。

        Returns:
            更新后的模板详情。
        """
        template = get_template_detail(pk)
        if template is None:
            return drf_error("未找到模板", status=404)
        ser = PublishTemplateWriteSerializer(template, data=request.data, partial=True, context={"request": request})
        if not ser.is_valid():
            return drf_error(str(ser.errors), status=400)
        template = ser.save()
        logger.info(
            "[PublishTemplateViewSet] [update_template] 更新模板：%s (id=%s)",
            template.template_name,
            template.id,
        )
        return drf_ok(PublishTemplateDetailSerializer(template).data)

    @action(detail=False, methods=["delete"], url_path=r"(?P<pk>[^/]+)")
    def delete_template(self, request, pk: str):
        """软删除模板（is_deleted=True）。

        Args:
            pk: 模板主键 ID。

        Returns:
            ``{deletedCount: 1}``。
        """
        template = get_template_detail(pk)
        if template is None:
            return drf_error("未找到模板", status=404)
        template.is_deleted = True
        template.save(update_fields=["is_deleted", "updated_at"])
        logger.info(
            "[PublishTemplateViewSet] [delete_template] 软删除模板 id=%s",
            pk,
        )
        return drf_ok({"deletedCount": 1})
