"""Listing 标签表（lx_listing_tag，managed=True）。

存储 Listing 全局标签信息，独立于商品标签体系。
"""
from django.db import models


class LxListingTag(models.Model):
    """Listing 标签表。

    每条记录对应一个全局标签定义，与 LxListingData.global_tags 中的标签 ID 关联。
    """

    STATUS_CHOICES = [
        ("creating", "创建中"),
        ("normal", "正常"),
        ("modifying", "修改中"),
        ("deleted", "已删除"),
    ]

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
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

    type = models.CharField(
        max_length=50,
        default="",
        verbose_name="标签类型",
    )

    color = models.CharField(
        max_length=20,
        default="",
        verbose_name="标签颜色",
    )

    create_by_name = models.CharField(
        max_length=100,
        default="",
        verbose_name="创建人名称",
    )

    modify_by_name = models.CharField(
        max_length=100,
        default="",
        verbose_name="最后编辑人名称",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="creating",
        verbose_name="状态",
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
        db_table = "lx_listing_tag"
        verbose_name = "Listing 标签"
        verbose_name_plural = "Listing 标签列表"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"LxListingTag<{self.global_tag_id}> {self.tag_name}"

    def save(self, *args, **kwargs):
        """保存时自动生成 global_tag_id。"""
        if not self.global_tag_id and self.id:
            self.global_tag_id = f"TAG_{self.id}"
        super().save(*args, **kwargs)
