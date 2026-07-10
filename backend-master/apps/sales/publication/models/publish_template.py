"""刊登模板模型（publish_template）。

存储用户创建的刊登模板，包含模板基本信息和 Amazon 属性数据（data_json）。
模板用于快速填充新建草稿时的动态字段值。
"""
from django.conf import settings
from django.db import models


class PublishTemplate(models.Model):
    """刊登模板。

    每条记录描述一个 productType 的模板，data_json 存储动态 Amazon 属性值，
    格式为 { attr_name: [{ marketplace_id, language_tag?, value }] }。
    """

    template_name = models.CharField(
        max_length=50,
        verbose_name="模板名称",
    )
    marketplace_id = models.CharField(
        max_length=64,
        verbose_name="市场ID",
        help_text="Amazon 市场 ID，如 A1PA6795UKMFR9",
    )
    product_type = models.CharField(
        max_length=255,
        verbose_name="商品类型",
        help_text="如 SHIRT",
    )
    product_type_unique_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="商品类型唯一ID",
    )
    country_code = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="国家代码",
    )
    data_json = models.JSONField(
        default=dict,
        verbose_name="模板数据",
        help_text="动态 Amazon 属性值，key=属性名，value=数组",
    )
    create_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_publish_templates",
        verbose_name="创建人",
    )
    update_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_publish_templates",
        verbose_name="更新人",
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="是否删除",
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
        managed = True
        db_table = "publish_template"
        verbose_name = "刊登模板"
        verbose_name_plural = "刊登模板"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.template_name} ({self.product_type})"
