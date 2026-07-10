"""Amazon 根分类查询选择器。

提供按 marketplace_id 查询根分类、子分类、搜索分类的只读逻辑。
"""
from typing import Optional

from apps.sales.publication.models.amazon_root_category import AmazonRootCategory


def get_root_categories(marketplace_id: str) -> list[AmazonRootCategory]:
    """查询指定市场的根分类列表。

    Args:
        marketplace_id: Amazon 市场 ID（如 A1PA6795UKMFR9）。

    Returns:
        根分类 QuerySet 列表（is_root=1）。
    """
    return list(
        AmazonRootCategory.objects.filter(
            marketplace_id=marketplace_id,
            is_root=1,
        ).order_by("category_name")
    )


def get_category_children(
    marketplace_id: str,
    category_unique_id: str,
) -> list[AmazonRootCategory]:
    """查询指定分类的子分类列表。

    通过父分类的 category_id 查找 parent_id 等于该值的子分类。

    Args:
        marketplace_id: Amazon 市场 ID。
        category_unique_id: 父分类的唯一 ID。

    Returns:
        子分类列表，父分类不存在时返回空列表。
    """
    parent = AmazonRootCategory.objects.filter(
        marketplace_id=marketplace_id,
        category_unique_id=category_unique_id,
    ).only("category_id").first()

    if parent is None:
        return []

    return list(
        AmazonRootCategory.objects.filter(
            marketplace_id=marketplace_id,
            parent_id=parent.category_id,
        ).order_by("category_name")
    )


def search_categories(
    marketplace_id: str,
    search_type: str,
    keyword: str,
) -> list[AmazonRootCategory]:
    """按关键词搜索分类。

    Args:
        marketplace_id: Amazon 市场 ID。
        search_type: 搜索类型（category_name / product_type_origin / category_id）。
        keyword: 搜索关键词。

    Returns:
        匹配的分类列表。
    """
    qs = AmazonRootCategory.objects.filter(marketplace_id=marketplace_id)

    if search_type == "category_name":
        qs = qs.filter(category_name__icontains=keyword)
    elif search_type == "product_type_origin":
        qs = qs.filter(product_type_origin__contains=keyword)
    elif search_type == "category_id":
        try:
            qs = qs.filter(category_id=int(keyword))
        except (ValueError, TypeError):
            return []
    else:
        qs = qs.filter(category_name__icontains=keyword)

    return list(qs.order_by("category_name")[:200])
