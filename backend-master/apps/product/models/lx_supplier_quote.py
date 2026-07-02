"""供应商报价表（lx_supplier_quote，managed=True）。

存储本地产品关联的供应商报价信息，含采购链接、报价梯度数据。
"""
from django.db import models

from apps.product.models.lx_local_product import LxLocalProduct


class PrimaryFlag(models.IntegerChoices):
    """首选供应商标记枚举。"""

    NO = 0, "否"
    YES = 1, "是"


class LxSupplierQuote(models.Model):
    """供应商报价表。

    每个产品可关联多条供应商报价，quotes 为 JSON 数组承载报价梯度。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    product = models.ForeignKey(
        LxLocalProduct,
        on_delete=models.CASCADE,
        db_column="product_id",
        related_name="supplier_quotes",
        verbose_name="关联产品",
    )

    psq_id = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="供应商报价 ID",
    )

    supplier_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="供应商 ID",
    )

    is_primary = models.IntegerField(
        choices=PrimaryFlag.choices,
        default=PrimaryFlag.NO,
        verbose_name="是否为首选供应商",
    )

    supplier_product_url = models.JSONField(
        null=True,
        blank=True,
        verbose_name="采购链接",
        help_text="字符串数组，每个元素为一个采购 URL",
    )

    quote_remark = models.TextField(
        blank=True,
        default="",
        verbose_name="供应商报价备注",
    )

    cg_price = models.CharField(
        max_length=30,
        default="",
        verbose_name="采购成本",
    )

    cg_currency_icon = models.CharField(
        max_length=10,
        default="",
        verbose_name="采购成本币种符号",
    )

    supplier_code = models.CharField(
        max_length=50,
        default="",
        verbose_name="供应商代码",
    )

    level_text = models.CharField(
        max_length=50,
        default="",
        verbose_name="级别",
    )

    employees_text = models.CharField(
        max_length=50,
        default="",
        verbose_name="规模",
    )

    remark = models.TextField(
        blank=True,
        default="",
        verbose_name="供应商备注",
    )

    supplier_name = models.CharField(
        max_length=255,
        default="",
        verbose_name="供应商名称",
    )

    # ── 复杂嵌套 ──────────────────────────────────────────────────────────────

    quotes = models.JSONField(
        null=True,
        blank=True,
        verbose_name="报价数据",
        help_text="数组，元素格式：{currency, currency_icon, is_tax, tax_rate, step_prices: [{moq, price, price_with_tax}]}",
    )

    class Meta:
        db_table = "lx_supplier_quote"
        verbose_name = "供应商报价"
        verbose_name_plural = "供应商报价列表"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"LxSupplierQuote<{self.psq_id}> {self.supplier_name}"
