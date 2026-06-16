"""利润报表-MSKU 模型（lx_profit_report_msku，managed=True）。

存储领星利润报表 MSKU 粒度的全量字段，唯一键为 dataDate+sid+msku+asin+deferredSubStatusCode。
"""
from django.db import models


class DetailFlag(models.IntegerChoices):
    """成本明细标记枚举。"""

    NO = 0, "无"
    YES = 1, "有"


class QueryType(models.IntegerChoices):
    """查询类型枚举。"""

    BY_DAY = 1, "按天"
    BY_MONTH = 2, "按月"


class LxProfitReportMsku(models.Model):
    """利润报表-MSKU（领星 → 财务 → 利润报表 MSKU）。

    以 dataDate + sid + msku + asin + deferredSubStatusCode 组成联合唯一约束。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    # ── 唯一键字段 ────────────────────────────────────────────────────────────

    query_type = models.IntegerField(
        choices=QueryType.choices,
        default=QueryType.BY_DAY,
        verbose_name="查询类型",
        help_text="1=按天，2=按月",
    )

    report_date_month = models.CharField(
        max_length=20,
        default="",
        verbose_name="按月时间",
    )

    sid = models.IntegerField(
        verbose_name="店铺 ID",
    )

    msku = models.CharField(
        max_length=200,
        default="",
        verbose_name="MSKU",
    )

    asin = models.CharField(
        max_length=50,
        default="",
        verbose_name="ASIN",
    )

    deferred_sub_status_code = models.CharField(
        max_length=50,
        default="",
        verbose_name="延时状态子状态码",
    )

    # ── 基础信息 ──────────────────────────────────────────────────────────────

    record_id = models.CharField(
        max_length=50,
        default="",
        verbose_name="记录 ID",
    )

    report_date_month = models.CharField(
        max_length=20,
        default="",
        verbose_name="按月时间",
    )

    posted_date_locale = models.CharField(
        max_length=20,
        default="",
        verbose_name="按天汇总",
    )

    is_display_detail = models.BooleanField(
        default=False,
        verbose_name="是否展示明细",
    )

    store_name = models.CharField(
        max_length=255,
        default="",
        verbose_name="店铺",
    )

    country = models.CharField(
        max_length=50,
        default="",
        verbose_name="国家",
    )

    country_code = models.CharField(
        max_length=10,
        default="",
        verbose_name="国家编码",
    )

    currency_code = models.CharField(
        max_length=10,
        default="",
        verbose_name="币种",
    )

    currency_icon = models.CharField(
        max_length=10,
        default="",
        verbose_name="币种符号",
    )

    # ── 商品信息 ──────────────────────────────────────────────────────────────

    small_image_url = models.CharField(
        max_length=512,
        default="",
        verbose_name="图片",
    )

    item_name = models.TextField(
        null=True,
        blank=True,
        verbose_name="标题",
    )

    local_name = models.CharField(
        max_length=255,
        default="",
        verbose_name="品名",
    )

    local_sku = models.CharField(
        max_length=200,
        default="",
        verbose_name="SKU",
    )

    parent_asin = models.CharField(
        max_length=50,
        default="",
        verbose_name="父 ASIN",
    )

    principal_realname = models.CharField(
        max_length=100,
        default="",
        verbose_name="负责人",
    )

    product_developer_realname = models.CharField(
        max_length=100,
        default="",
        verbose_name="产品开发负责人",
    )

    category_name = models.CharField(
        max_length=100,
        default="",
        verbose_name="分类",
    )

    brand_name = models.CharField(
        max_length=100,
        default="",
        verbose_name="品牌",
    )

    listing_tag_ids = models.CharField(
        max_length=512,
        default="",
        verbose_name="Listing 标签 ID",
    )

    # ── 状态 ──────────────────────────────────────────────────────────────────

    transaction_status = models.CharField(
        max_length=50,
        default="",
        verbose_name="交易状态",
    )

    transaction_status_code = models.CharField(
        max_length=50,
        default="",
        verbose_name="交易状态码",
    )

    # ── 成本明细标记 ──────────────────────────────────────────────────────────

    has_cg_price_detail = models.IntegerField(
        choices=DetailFlag.choices,
        default=DetailFlag.NO,
        verbose_name="是否有采购成本明细",
    )

    has_cg_transport_costs_detail = models.IntegerField(
        choices=DetailFlag.choices,
        default=DetailFlag.NO,
        verbose_name="是否有物流（头程）成本明细",
    )

    has_cg_other_costs_detail = models.IntegerField(
        choices=DetailFlag.choices,
        default=DetailFlag.NO,
        verbose_name="是否有其他成本明细",
    )

    # ── 成本明细内容 ──────────────────────────────────────────────────────────

    cg_price_details = models.TextField(
        blank=True,
        default="",
        verbose_name="采购成本详情",
    )

    cg_transport_costs_details = models.TextField(
        blank=True,
        default="",
        verbose_name="头程成本详情",
    )

    cg_other_costs_details = models.TextField(
        blank=True,
        default="",
        verbose_name="其他成本详情",
    )

    # ── 自定义费用 ────────────────────────────────────────────────────────────

    other_fee_str = models.JSONField(
        null=True,
        blank=True,
        verbose_name="自定义费用信息",
        help_text="数组，元素格式：{otherFeeTypeId, otherFeeName, feeAllocation}",
    )

    # ── 销量 ──────────────────────────────────────────────────────────────────

    total_fba_fbm_quantity = models.IntegerField(
        default=0,
        verbose_name="FBA 和 FBM 销量加总",
    )

    total_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="销量",
    )

    fba_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="FBA 销量",
    )

    fbm_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="FBM 销量",
    )

    total_reship_quantity = models.IntegerField(
        default=0,
        verbose_name="补换货量",
    )

    reship_fbm_product_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="FBM 补（换）货量",
    )

    reship_fbm_product_sale_refunds_quantity = models.IntegerField(
        default=0,
        verbose_name="FBM 补（换）货退回量",
    )

    reship_fba_product_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="FBA 补（换）货量",
    )

    reship_fba_product_sale_refunds_quantity = models.IntegerField(
        default=0,
        verbose_name="FBA 补（换）货退回量",
    )

    mc_fba_fulfillment_fees_quantity = models.IntegerField(
        default=0,
        verbose_name="多渠道销量",
    )

    total_ads_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="广告销量",
    )

    ads_sd_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="SD 广告销量",
    )

    ads_sp_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="SP 广告销量",
    )

    shared_ads_sb_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="SB 广告销量",
    )

    shared_ads_sbv_sales_quantity = models.IntegerField(
        default=0,
        verbose_name="SBV 广告销量",
    )

    cg_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="成本数量",
    )

    fba_inventory_credit_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="赔偿量",
    )

    disposal_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="销毁量",
    )

    removal_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="移除量",
    )

    # ── 退款 / 退货量 ─────────────────────────────────────────────────────────

    refunds_quantity = models.IntegerField(
        default=0,
        verbose_name="退款量",
    )

    refunds_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0.0000,
        verbose_name="退款率",
    )

    fba_returns_quantity = models.IntegerField(
        default=0,
        verbose_name="退货量",
    )

    fba_returns_saleable_quantity = models.IntegerField(
        default=0,
        verbose_name="退货量（可售）",
    )

    fba_returns_unsaleable_quantity = models.IntegerField(
        default=0,
        verbose_name="退货量（不可售）",
    )

    fba_returns_quantity_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0.0000,
        verbose_name="退货率",
    )

    # ── 销售额 ────────────────────────────────────────────────────────────────

    total_fba_fbm_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 和 FBM 销售额加总",
    )

    total_sales_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="销售额",
    )

    fba_sale_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 销售额",
    )

    fbm_sale_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBM 销售额",
    )

    shipping_credits = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="买家运费",
    )

    promotional_rebates = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="促销折扣",
    )

    fba_inventory_credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 库存赔偿",
    )

    cash_on_delivery = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="COD",
    )

    other_in_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="其他收入",
    )

    fba_liquidation_proceeds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="清算收入",
    )

    fba_liquidation_proceeds_adjustments = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="清算调整",
    )

    amazon_shipping_reimbursement = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="亚马逊运费赔偿",
    )

    safe_t_reimbursement = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Safe-T 索赔",
    )

    netco_transaction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Netco 交易",
    )

    reimbursements = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="赔偿收入",
    )

    clawbacks = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="追索收入",
    )

    shared_commingling_vat_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="混合 VAT 收入",
    )

    gift_wrap_credits = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="包装收入",
    )

    guarantee_claims = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="买家交易保障索赔额",
    )

    cost_of_po_integers_granted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="积分抵减收入",
    )

    others = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="平台收入中其他收入的其他费用",
    )

    platform_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="平台收入",
    )

    # ── 收入退款 ──────────────────────────────────────────────────────────────

    total_sales_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="收入退款额",
    )

    fba_sales_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 销售退款额",
    )

    fbm_sales_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBM 销售退款额",
    )

    shipping_credit_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="买家运费退款额",
    )

    gift_wrap_credit_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="买家包装退款额",
    )

    chargebacks = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="买家拒付",
    )

    cost_of_po_integers_returned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="积分抵减退回",
    )

    promotional_rebate_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="促销折扣退款额",
    )

    # ── 费用退款 ──────────────────────────────────────────────────────────────

    total_fee_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="费用退款额",
    )

    selling_fee_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="平台费退款额",
    )

    fba_transaction_fee_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="发货费退款额",
    )

    refund_administration_fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="交易费用退款额",
    )

    other_transaction_fee_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="其他订单费退款额",
    )

    refund_for_advertiser = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="广告退款额",
    )

    shipping_label_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="运输标签费退款",
    )

    # ── 广告销售额 ────────────────────────────────────────────────────────────

    total_ads_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="广告销售额",
    )

    ads_sd_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="SD 广告销售额",
    )

    ads_sp_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="SP 广告销售额",
    )

    shared_ads_sb_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="SB 广告销售额",
    )

    shared_ads_sbv_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="SBV 广告销售额",
    )

    # ── 广告费 ────────────────────────────────────────────────────────────────

    total_ads_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="广告费",
    )

    ads_sp_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="SP 广告费",
    )

    ads_sb_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="SB 广告费",
    )

    ads_sbv_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="SBV 广告费",
    )

    ads_sd_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="SD 广告费",
    )

    shared_cost_of_advertising = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="差异分摊",
    )

    shared_ads_al_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Live 广告",
    )

    shared_ads_cc_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="创作者计划",
    )

    shared_ads_sspaot_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="TV 广告",
    )

    shared_ads_sar_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="零售商赞助广告",
    )

    # ── 推广费 ────────────────────────────────────────────────────────────────

    promotion_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="推广费",
    )

    shared_subscription_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="订阅费",
    )

    shared_ld_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="秒杀费",
    )

    shared_coupon_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="优惠券",
    )

    shared_early_reviewer_program_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="早期评论人计划",
    )

    shared_vine_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Vine",
    )

    # ── 订单费用 ──────────────────────────────────────────────────────────────

    fba_delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 发货费",
    )

    mc_fba_delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 发货费（多渠道）",
    )

    total_fba_delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 发货费合计",
    )

    other_transaction_fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="其他订单费用",
    )

    points_adjusted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="积分费用",
    )

    shared_fba_transaction_customer_return_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="亚马逊客户物流退货费",
    )

    shared_fba_customer_return_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 卖家退回费",
    )

    custom_order_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="订单其他费",
    )

    custom_order_fee_principal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="站外推广费-本金",
    )

    custom_order_fee_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="站外推广费-佣金",
    )

    # ── FBA 仓储费 ────────────────────────────────────────────────────────────

    total_storage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 仓储费",
    )

    fba_storage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="月度仓库费",
    )

    shared_fba_storage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="月度仓储费差异",
    )

    long_term_storage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="长期仓储费",
    )

    shared_long_term_storage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="长期仓储费差异",
    )

    shared_storage_renewal_billing = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="库存续订费用",
    )

    fba_storage_fee_accrual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="月仓储费-本月计提",
    )

    fba_storage_fee_accrual_difference = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="月仓储费-上月冲销",
    )

    long_term_storage_fee_accrual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="长期仓储费-本月计提",
    )

    long_term_storage_fee_accrual_difference = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="长期仓储费-上月冲销",
    )

    shared_fba_disposal_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 销毁费",
    )

    shared_fba_removal_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 移除费",
    )

    shared_fba_overage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="超量仓储费",
    )

    shared_other_fba_inventory_fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="其他仓储费",
    )

    # ── FBA 其他费 ────────────────────────────────────────────────────────────

    shared_fba_inbound_transportation_program_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="入仓手续费",
    )

    shared_fba_inbound_convenience_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="入库配置费",
    )

    shared_fba_inbound_defect_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 仓储费入库缺陷费",
    )

    shared_fba_international_inbound_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="FBA 国际物流货运费",
    )

    shared_labeling_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="标签费",
    )

    shared_polybagging_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="塑料包装费",
    )

    shared_bubblewrap_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="泡沫包装费",
    )

    shared_taping_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="胶带费",
    )

    shared_amazon_partnered_carrier_shipment_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="合作承运费",
    )

    shared_item_fee_adjustment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="库存调整费用",
    )

    # ── AWD 费用 ──────────────────────────────────────────────────────────────

    shared_awd_processing_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="AWD 处理费",
    )

    shared_awd_transportation_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="AWD 运输费",
    )

    shared_awd_storage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="AWD 仓储费",
    )

    shared_star_storage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="卫星仓仓储费",
    )

    # ── 平台其他费 ────────────────────────────────────────────────────────────

    total_platform_other_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="平台其他费",
    )

    shipping_label_purchases = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="运输标签费",
    )

    shared_carrier_shipping_label_adjustments = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="承运人装运标签调整费",
    )

    shared_liquidations_fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="清算费",
    )

    shared_manual_processing_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="人工处理费用",
    )

    shared_other_service_fees = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="其他服务费",
    )

    shared_mfn_postage_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="多渠道邮资费",
    )

    adjustments = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="调整费用",
    )

    platform_expense = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="平台支出",
    )

    # ── 税 ────────────────────────────────────────────────────────────────────

    total_sales_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="销售税",
    )

    tcs_igst_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="TCS-IGST",
    )

    tcs_sgst_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="TCS-SGST",
    )

    tcs_cgst_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="TCS-CGST",
    )

    shared_commingling_vat_expenses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="混合 VAT",
    )

    tax_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="VAT/GST",
    )

    tax_collected_product = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="商品价格税",
    )

    tax_collected_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="促销折扣税",
    )

    tax_collected_shipping = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="买家运费税",
    )

    tax_collected_gift_wrap = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="礼品包装税",
    )

    shared_tax_adjustment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="商品税调整",
    )

    # ── 税退款 ────────────────────────────────────────────────────────────────

    sales_tax_refund = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="销售税退款额",
    )

    tcs_igst_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="TCS-IGST（退款）",
    )

    tcs_sgst_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="TCS-SGST（退款）",
    )

    tcs_cgst_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="TCS-CGST（退款）",
    )

    tax_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="VAT/GST（退款）",
    )

    tax_refunded_product = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="商品价格税退款",
    )

    tax_refunded_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="促销折扣税退款",
    )

    tax_refunded_shipping = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="买家运费税退款",
    )

    tax_refunded_gift_wrap = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="礼品包装税退款",
    )

    sales_tax_withheld = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="市场税",
    )

    refund_tax_withheld = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="市场税退款额",
    )

    tds_section_194o_net = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="混合网路费用",
    )

    gross_profit_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="合计税费",
    )

    # ── 成本 ──────────────────────────────────────────────────────────────────

    cg_price_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="采购成本",
    )

    cg_price_abs_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="采购成本绝对值",
    )

    cg_unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="采购均价",
    )

    proportion_of_cg = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0.0000,
        verbose_name="采购占比",
    )

    cg_transport_costs_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="头程成本",
    )

    cg_transport_unit_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="头程均价",
    )

    proportion_of_cg_transport = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0.0000,
        verbose_name="头程占比",
    )

    cg_other_costs_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="其他成本",
    )

    cg_other_unit_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="其他均价",
    )

    proportion_of_cg_other_costs = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0.0000,
        verbose_name="其他成本占比",
    )

    # ── 合计成本 ──────────────────────────────────────────────────────────────

    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="合计成本",
    )

    proportion_of_total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0.0000,
        verbose_name="合计成本占比",
    )

    # ── 利润 ──────────────────────────────────────────────────────────────────

    gross_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="毛利润",
    )

    gross_profit_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="毛利润收入",
    )

    gross_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0.0000,
        verbose_name="毛利率",
    )

    class Meta:
        db_table = "lx_profit_report_msku"
        verbose_name = "利润报表-MSKU"
        verbose_name_plural = "利润报表-MSKU 列表"
        ordering = ["-report_date_month", "-id"]
        unique_together = (
            ("report_date_month", "posted_date_locale", "sid", "msku", "asin", "deferred_sub_status_code"),
        )

    def __str__(self) -> str:
        return f"LxProfitReportMsku<{self.msku}> {self.report_date_month} sid={self.sid}"
