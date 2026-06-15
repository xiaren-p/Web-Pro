"""产品自定义字段表（lx_product_custom_field，managed=True）。

存储本地产品关联的自定义字段键值对，每个字段对应一条记录。
"""
from django.db import models

from api_v1.models.lingxing.product.lx_local_product import LxLocalProduct


class LxProductCustomField(models.Model):
    """产品自定义字段表。

    每个产品可定义多个自定义字段，字段名和值均为文本存储。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    product = models.ForeignKey(
        LxLocalProduct,
        on_delete=models.CASCADE,
        db_column="product_id",
        related_name="custom_fields",
        verbose_name="关联产品",
    )

    field_id = models.CharField(
        max_length=50,
        default="",
        verbose_name="字段 ID",
    )

    field_name = models.CharField(
        max_length=100,
        default="",
        verbose_name="字段名称",
    )

    val_text = models.TextField(
        blank=True,
        default="",
        verbose_name="字段值",
    )

    class Meta:
        db_table = "lx_product_custom_field"
        verbose_name = "产品自定义字段"
        verbose_name_plural = "产品自定义字段列表"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"LxProductCustomField<{self.field_id}> {self.field_name}"
