"""刊登模板查询选择器。

提供分页列表查询（按模板名称搜索）和单条详情查询。
"""
from django.db.models import QuerySet

from apps.sales.publication.models.publish_template import PublishTemplate


def get_template_page_qs(keyword: str | None = None) -> QuerySet[PublishTemplate]:
    """构建模板分页查询集（排除已软删除的记录）。

    Args:
        keyword: 模板名称模糊搜索关键词。

    Returns:
        PublishTemplate QuerySet，按更新时间倒序。
    """
    qs = PublishTemplate.objects.filter(is_deleted=False)
    if keyword:
        qs = qs.filter(template_name__icontains=keyword)
    return qs.order_by("-updated_at")


def get_template_detail(pk: str) -> PublishTemplate | None:
    """按主键获取模板详情（排除已软删除的记录）。

    Args:
        pk: 模板主键 ID。

    Returns:
        PublishTemplate 实例，未找到或已删除时返回 None。
    """
    return PublishTemplate.objects.filter(id=pk, is_deleted=False).first()
