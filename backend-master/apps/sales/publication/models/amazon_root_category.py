"""Amazon 根分类模型（lx_amazon_root_category）。

存储从领星接口同步的 Amazon 分类数据，包含根类目及子类目信息。
"""
from django.db import models


class AmazonRootCategory(models.Model):
    """Amazon 根分类。

    对应领星接口返回的 data.category 节点，category_unique_id + marketplace_id
    构成联合唯一标识。
    """

    category_unique_id = models.CharField(
        max_length=64,
        verbose_name="类目唯一ID",
        help_text="如 107883898167361544",
    )
    category_name = models.CharField(
        max_length=255,
        verbose_name="类目名称",
        help_text="如 Amazon Instant Video",
    )
    category_id = models.BigIntegerField(
        verbose_name="亚马逊定义的类目ID",
        help_text="如 16261641",
    )
    marketplace_id = models.CharField(
        max_length=64,
        verbose_name="市场ID",
    )
    parent_id = models.BigIntegerField(
        verbose_name="父级ID",
        default=0,
        help_text="0 表示根类目",
    )
    is_root = models.IntegerField(
        verbose_name="是否为根类目",
        default=0,
        help_text="1 为根，0 为子",
    )
    has_children = models.IntegerField(
        verbose_name="是否包含子类目",
        default=0,
        help_text="1 有，0 无",
    )
    child_categories = models.JSONField(
        verbose_name="子类目ID列表",
        default=list,
        help_text="如 ['16386761', '16262841']",
    )
    product_type_origin = models.JSONField(
        verbose_name="商品原始类型",
        default=list,
        help_text="如 ['ADVERTISEMENT_COLLECTIBLES']",
    )
    browse_node_attributes = models.JSONField(
        verbose_name="类目节点属性",
        default=dict,
    )
    category_path_id = models.JSONField(
        verbose_name="类目路径ID",
        default=dict,
    )
    category_path_name = models.JSONField(
        verbose_name="类目路径名称",
        default=dict,
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
        db_table = "lx_amazon_root_category"
        verbose_name = "Amazon 根分类"
        verbose_name_plural = "Amazon 根分类"
        ordering = ["category_unique_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["category_unique_id", "marketplace_id"],
                name="uq_amazon_root_category",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.category_name} ({self.category_unique_id}, {self.marketplace_id})"
