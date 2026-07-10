"""Amazon 商品类型 Schema 查询选择器。

提供按 marketplace_id + product_type_origin 查询单条 Schema 的只读逻辑。
"""
from apps.sales.publication.models.amazon_product_type_schema import AmazonProductTypeSchema


def get_product_type_schema(
    marketplace_id: str,
    product_type_origin: str,
) -> AmazonProductTypeSchema | None:
    """按市场 ID + 商品类型查询 Schema 记录。

    Args:
        marketplace_id: Amazon 市场 ID（如 A1PA6795UKMFR9）。
        product_type_origin: 商品类型标识（如 SHIRT）。

    Returns:
        AmazonProductTypeSchema 实例，未找到时返回 None。
    """
    return (
        AmazonProductTypeSchema.objects.filter(
            marketplace_id=marketplace_id,
            product_type_origin=product_type_origin,
        )
        .only(
            "product_type_unique_id",
            "marketplace_id",
            "product_type_origin",
            "display_name",
            "properties",
            "properties_zh",
        )
        .first()
    )
