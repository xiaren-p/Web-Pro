"""Listing 完整数据快照表（lx_listing_data）。

存储领星 /data/mws/listing/getList 接口返回的全量字段，
包含 Listing 基础属性、库存、价格、销量、评论、排名及尺寸信息。
"""
from django.db import models


class ListingStatus(models.IntegerChoices):
    """Listing 上架状态枚举。"""

    OFFLINE = 0, "停售"
    ONLINE = 1, "在售"


class ListingDeleteFlag(models.IntegerChoices):
    """Listing 删除标记枚举。"""

    NO = 0, "未删除"
    YES = 1, "已删除"


class ListingStoreType(models.IntegerChoices):
    """Listing 商品类型枚举。"""

    NORMAL = 1, "非低价商店"
    LOW_PRICE = 2, "低价商店"


class LxListingData(models.Model):
    """Listing 完整数据快照表（领星 → 销售 → Listing）。

    以 seller_sku + sid 组成复合唯一索引，支持按店铺做 upsert。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    # ── 基础标识 ──────────────────────────────────────────────────────────────

    listing_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Listing ID",
        help_text="亚马逊定义的 Listing ID，可能为空",
    )

    sid = models.IntegerField(
        verbose_name="店铺 ID",
    )

    marketplace = models.CharField(
        max_length=50,
        default="",
        verbose_name="国家/站点",
    )

    seller_sku = models.CharField(
        max_length=200,
        default="",
        verbose_name="MSKU",
    )

    fnsku = models.CharField(
        max_length=100,
        default="",
        verbose_name="FNSKU",
    )

    asin = models.CharField(
        max_length=50,
        default="",
        verbose_name="ASIN",
    )

    parent_asin = models.CharField(
        max_length=50,
        default="",
        verbose_name="父体 ASIN",
    )

    small_image_url = models.CharField(
        max_length=512,
        default="",
        verbose_name="商品缩略图地址",
    )

    # ── 状态 ──────────────────────────────────────────────────────────────────

    status = models.IntegerField(
        choices=ListingStatus.choices,
        default=ListingStatus.ONLINE,
        verbose_name="上架状态",
    )

    is_delete = models.IntegerField(
        choices=ListingDeleteFlag.choices,
        default=ListingDeleteFlag.NO,
        verbose_name="是否已删除",
    )

    # ── 商品信息 ──────────────────────────────────────────────────────────────

    item_name = models.TextField(
        null=True,
        blank=True,
        verbose_name="标题",
    )

    local_sku = models.CharField(
        max_length=200,
        default="",
        verbose_name="本地产品 SKU",
    )

    local_name = models.CharField(
        max_length=255,
        default="",
        verbose_name="品名",
    )

    fulfillment_channel_type = models.CharField(
        max_length=20,
        default="",
        verbose_name="配送方式",
        help_text="FBM / FBA",
    )

    store_type = models.IntegerField(
        choices=ListingStoreType.choices,
        default=ListingStoreType.NORMAL,
        verbose_name="商品类型",
    )

    # ── 价格 ──────────────────────────────────────────────────────────────────

    currency_code = models.CharField(
        max_length=10,
        default="",
        verbose_name="币种",
    )

    price = models.CharField(
        max_length=30,
        default="0.00",
        verbose_name="价格（不含促销/运费/积分）",
    )

    landed_price = models.CharField(
        max_length=30,
        default="0.00",
        verbose_name="总价（含促销/运费/积分）",
    )

    listing_price = models.CharField(
        max_length=30,
        default="0.00",
        verbose_name="优惠价",
    )

    shipping = models.CharField(
        max_length=30,
        default="0.00",
        verbose_name="运费",
    )

    points = models.CharField(
        max_length=30,
        default="",
        verbose_name="积分",
        help_text="仅日本站有效",
    )

    # ── 库存 ──────────────────────────────────────────────────────────────────

    quantity = models.IntegerField(
        default=0,
        verbose_name="FBM 库存",
    )

    afn_fulfillable_quantity = models.IntegerField(
        default=0,
        verbose_name="FBA 可售",
    )

    afn_unsellable_quantity = models.IntegerField(
        default=0,
        verbose_name="FBA 不可售",
    )

    reserved_fc_transfers = models.IntegerField(
        default=0,
        verbose_name="待调仓",
    )

    reserved_fc_processing = models.IntegerField(
        default=0,
        verbose_name="调仓中",
    )

    reserved_customerorders = models.IntegerField(
        default=0,
        verbose_name="待发货",
    )

    afn_inbound_shipped_quantity = models.IntegerField(
        default=0,
        verbose_name="在途",
    )

    afn_inbound_working_quantity = models.IntegerField(
        default=0,
        verbose_name="计划入库",
    )

    afn_inbound_receiving_quantity = models.IntegerField(
        default=0,
        verbose_name="入库中",
    )

    # ── 销量 / 销售额 ──────────────────────────────────────────────────────────

    total_volume = models.CharField(
        max_length=30,
        default="0",
        verbose_name="销量 7 天",
    )

    yesterday_volume = models.CharField(
        max_length=30,
        default="0",
        verbose_name="销量昨天",
    )

    fourteen_volume = models.CharField(
        max_length=30,
        default="0",
        verbose_name="销量 14 天",
    )

    thirty_volume = models.CharField(
        max_length=30,
        default="0",
        verbose_name="销量 30 天",
    )

    average_seven_volume = models.CharField(
        max_length=30,
        default="0",
        verbose_name="日均销量 7 日",
    )

    average_fourteen_volume = models.CharField(
        max_length=30,
        default="0",
        verbose_name="日均销量 14 日",
    )

    average_thirty_volume = models.CharField(
        max_length=30,
        default="0",
        verbose_name="日均销量 30 日",
    )

    yesterday_amount = models.CharField(
        max_length=30,
        default="0.00",
        verbose_name="销售额昨天",
    )

    seven_amount = models.CharField(
        max_length=30,
        default="0.00",
        verbose_name="销售额 7 天",
    )

    fourteen_amount = models.CharField(
        max_length=30,
        default="0.00",
        verbose_name="销售额 14 天",
    )

    thirty_amount = models.CharField(
        max_length=30,
        default="0.00",
        verbose_name="销售额 30 天",
    )

    # ── 排名 / 评论 ───────────────────────────────────────────────────────────

    seller_rank = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="大类排名",
    )

    seller_brand = models.CharField(
        max_length=255,
        default="",
        verbose_name="亚马逊品牌",
    )

    seller_category = models.TextField(
        null=True,
        blank=True,
        verbose_name="大类类目（旧，后续不再维护）",
    )

    seller_category_new = models.JSONField(
        null=True,
        blank=True,
        verbose_name="大类类目",
        help_text="数组，如 [\"Beauty & Personal Care\"]",
    )

    small_rank = models.JSONField(
        null=True,
        blank=True,
        verbose_name="小类排名信息",
        help_text="数组，元素格式：{category, rank}",
    )

    review_num = models.IntegerField(
        default=0,
        verbose_name="评论条数",
    )

    last_star = models.CharField(
        max_length=10,
        default="0",
        verbose_name="星级评分",
    )

    # ── 时间 ──────────────────────────────────────────────────────────────────

    open_date = models.CharField(
        max_length=100,
        default="",
        verbose_name="商品创建时间（带时区原始字符串）",
    )

    open_date_display = models.CharField(
        max_length=100,
        default="",
        verbose_name="商品创建时间（格式化含时区）",
    )

    listing_update_date = models.CharField(
        max_length=50,
        default="",
        verbose_name="Listing 报表更新时间（UTC）",
    )

    pair_update_time = models.CharField(
        max_length=50,
        default="",
        verbose_name="配对更新时间（北京时间）",
    )

    first_order_time = models.CharField(
        max_length=20,
        default="",
        verbose_name="首单时间（Y-m-d）",
    )

    on_sale_time = models.CharField(
        max_length=20,
        default="",
        verbose_name="开售时间（Y-m-d）",
    )

    # ── 复杂嵌套 ──────────────────────────────────────────────────────────────

    principal_info = models.JSONField(
        null=True,
        blank=True,
        verbose_name="负责人信息",
        help_text="数组，元素格式：{principal_uid, principal_name}",
    )

    dimension_info = models.JSONField(
        null=True,
        blank=True,
        verbose_name="尺寸信息",
        help_text="数组，包含商品与包装的长宽高重及单位",
    )

    global_tags = models.JSONField(
        null=True,
        blank=True,
        verbose_name="全局标签",
        help_text="数组，元素格式：{globalTagId, tagName, color}",
    )

    class Meta:
        db_table = "lx_listing_data"
        verbose_name = "Listing 完整数据快照"
        verbose_name_plural = "Listing 完整数据快照列表"
        ordering = ["-id"]
        unique_together = (("seller_sku", "sid"),)

    def __str__(self) -> str:
        return f"LxListingData<{self.seller_sku}> sid={self.sid}"
