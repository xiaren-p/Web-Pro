"""产品标签表（lx_product_tag，managed=True）。

存储本地产品关联的全局标签信息，每条标签对应一个产品。
"""
from django.db import models

from api_v1.models.lingxing.product.lx_local_product import LxLocalProduct


class LxProductTag(models.Model):
    """产品标签表。

    每个产品可绑定多条标签，通过 ForeignKey 关联 LxLocalProduct。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    product = models.ForeignKey(
        LxLocalProduct,
        on_delete=models.CASCADE,
        db_column="product_id",
        related_name="tags",
        verbose_name="关联产品",
    )

    global_tag_id = models.CharField(
        max_length=50,
        default="",
        verbose_name="标签 ID",
    )

    tag_name = models.CharField(
        max_length=100,
        default="",
        verbose_name="标签名称",
    )

    color = models.CharField(
        max_length=20,
        default="",
        verbose_name="标签颜色",
    )

    class Meta:
        db_table = "lx_product_tag"
        verbose_name = "产品标签"
        verbose_name_plural = "产品标签列表"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"LxProductTag<{self.global_tag_id}> {self.tag_name}"
