"""Amazon 商品类型 JSON Schema 模型（lx_amazon_product_type）。

存储从领星接口同步的 Amazon productType 对应的 JSON Schema 定义，
包含站点语言版本及中文版本。
"""
from django.db import models


class AmazonProductTypeSchemaSchema(models.Model):
    """Amazon 商品类型 JSON Schema。

    对应领星接口返回的 data.productType 节点，product_type_unique_id 为主键。
    每条记录描述一个 productType 的 JSON Schema 结构定义。
    """

    product_type_unique_id = models.CharField(
        primary_key=True,
        max_length=64,
        verbose_name="商品类型唯一ID",
        help_text="如 514829689877954560",
    )
    marketplace_id = models.CharField(
        max_length=64,
        verbose_name="市场ID",
    )
    product_type_origin = models.CharField(
        max_length=255,
        verbose_name="商品类型",
        help_text="如 ADVERTISEMENT_COLLECTIBLES",
    )
    display_name = models.CharField(
        max_length=255,
        verbose_name="商品类型名称",
        help_text="如 ADVERTISEMENT_COLLECTIBLES",
    )
    properties = models.TextField(
        verbose_name="JSON Schema（站点语言版本）",
        blank=True,
        default="",
    )
    properties_zh = models.TextField(
        verbose_name="JSON Schema（中文版本）",
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_amazon_product_type"
        verbose_name = "Amazon 商品类型 JSON Schema"
        verbose_name_plural = "Amazon 商品类型 JSON Schema"
        ordering = ["product_type_unique_id"]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.product_type_unique_id})"
