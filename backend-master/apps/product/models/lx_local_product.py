"""本地产品主表（lx_local_product，managed=True）。

存储本地产品基础信息，包含 SKU、品牌、采购、开发人员及产品属性等字段。
"""
from django.db import models


class ProductOpenStatus(models.IntegerChoices):
    """产品启用状态枚举。"""

    DISABLED = 0, "停用"
    ENABLED = 1, "启用"


class ProductStatus(models.IntegerChoices):
    """产品状态枚举。"""

    STOP_SELLING = 0, "停售"
    ON_SALE = 1, "在售"
    DEVELOPING = 2, "开发中"
    CLEARANCE = 3, "清仓"


class ComboFlag(models.IntegerChoices):
    """组合产品标记枚举。"""

    NO = 0, "否"
    YES = 1, "是"


class LxLocalProduct(models.Model):
    """本地产品主表（领星 → 产品 → 本地产品）。

    每条记录对应一个本地 SKU 产品，关联品牌、类别、供应商等信息。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    # ── 基础标识 ──────────────────────────────────────────────────────────────

    cid = models.IntegerField(
        verbose_name="类别 ID",
    )

    category_name = models.CharField(
        max_length=100,
        default="",
        verbose_name="类别名称",
    )

    bid = models.IntegerField(
        verbose_name="品牌 ID",
    )

    brand_name = models.CharField(
        max_length=100,
        default="",
        verbose_name="品牌名称",
    )

    sku = models.CharField(
        max_length=200,
        default="",
        verbose_name="本地产品 SKU",
    )

    sku_identifier = models.CharField(
        max_length=200,
        default="",
        verbose_name="SKU 识别码",
    )

    product_name = models.CharField(
        max_length=255,
        default="",
        verbose_name="品名",
    )

    pic_url = models.CharField(
        max_length=512,
        default="",
        verbose_name="图片链接",
    )

    # ── SPU 关联 ──────────────────────────────────────────────────────────────

    ps_id = models.IntegerField(
        verbose_name="SPU 唯一 ID",
    )

    spu = models.CharField(
        max_length=100,
        default="",
        verbose_name="SPU",
    )

    # ── 采购信息 ──────────────────────────────────────────────────────────────

    cg_delivery = models.IntegerField(
        verbose_name="采购交期（天）",
    )

    cg_transport_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="采购运输成本",
    )

    purchase_remark = models.TextField(
        blank=True,
        default="",
        verbose_name="采购备注",
    )

    cg_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="采购成本（人民币）",
    )

    cg_opt_uid = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="采购员 UID",
    )

    cg_opt_username = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="采购员名称",
    )

    # ── 状态 ──────────────────────────────────────────────────────────────────

    open_status = models.IntegerField(
        choices=ProductOpenStatus.choices,
        default=ProductOpenStatus.ENABLED,
        verbose_name="产品启用状态",
    )

    status = models.IntegerField(
        choices=ProductStatus.choices,
        default=ProductStatus.ON_SALE,
        verbose_name="产品状态",
    )

    status_text = models.CharField(
        max_length=50,
        default="",
        verbose_name="状态文本",
    )

    is_combo = models.IntegerField(
        choices=ComboFlag.choices,
        default=ComboFlag.NO,
        verbose_name="是否为组合产品",
    )

    # ── 人员 ──────────────────────────────────────────────────────────────────

    product_developer_uid = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="开发人员 UID",
    )

    product_developer = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="开发人员名称",
    )

    # ── 复杂嵌套 ──────────────────────────────────────────────────────────────

    attribute = models.JSONField(
        null=True,
        blank=True,
        verbose_name="产品属性",
        help_text="数组，元素格式：{attr_id, attr_name, attr_value}",
    )

    # ── 关联 ID 列表（冗余存储，方便反查）──────────────────────────────────────

    tag_ids = models.JSONField(
        null=True,
        blank=True,
        verbose_name="标签 ID 列表",
        help_text="产品关联的标签 ID 数组，如 [\"907204347399528686\"]",
    )

    supplier_quote_ids = models.JSONField(
        null=True,
        blank=True,
        verbose_name="供应商报价 ID 列表",
        help_text="产品关联的供应商报价 psq_id 数组，如 [\"psq_001\", \"psq_002\"]",
    )

    custom_field_ids = models.JSONField(
        null=True,
        blank=True,
        verbose_name="自定义字段 ID 列表",
        help_text="产品关联的自定义字段 field_id 数组，如 [\"field_001\"]",
    )

    # ── 时间 ──────────────────────────────────────────────────────────────────

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        managed = False  # 外部数据表，Django 不管理 schema
        db_table = "lx_local_product"
        verbose_name = "本地产品"
        verbose_name_plural = "本地产品列表"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"LxLocalProduct<{self.sku}> {self.product_name}"
