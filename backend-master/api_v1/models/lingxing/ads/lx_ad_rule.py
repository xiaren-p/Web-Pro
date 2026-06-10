"""广告规则策略 — 草稿规则表（lx_ad_rule）。"""
from django.db import models


class AdRuleStatus(models.TextChoices):
    """规则状态枚举。"""

    ACTIVE = "active", "启用"
    INACTIVE = "inactive", "暂停"


class EffectiveType(models.TextChoices):
    """生效周期类型枚举。"""

    WITHIN_DAYS = "within_days", "指定天数内"
    BEYOND_DAYS = "beyond_days", "指定天数之外"
    DATE_RANGE = "date_range", "日期范围"


class ComparisonTarget(models.TextChoices):
    """比对对象类型枚举。"""

    CAMPAIGN = "campaign", "广告活动"
    AD_GROUP = "ad_group", "广告组"
    SEARCH_TERMS = "search_terms", "用户搜索词"
    TARGETING = "targeting", "投放"


class AddKeywordMatchType(models.TextChoices):
    """关键词匹配方式枚举。"""

    BROAD = "broad", "广泛匹配"
    PHRASE = "phrase", "词组匹配"
    EXACT = "exact", "精准匹配"


class AddKeywordBidType(models.TextChoices):
    """关键词竞价方式枚举。"""

    ACTUAL_CPC = "actual_cpc", "采用实际出单 CPC"
    FIXED = "fixed", "填写固定值"


class LxAdRule(models.Model):
    """广告规则策略 — 草稿规则表（领星 → 广告 → 规则策略 → 规则）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="规则名称",
    )

    status = models.CharField(
        max_length=20,
        choices=AdRuleStatus.choices,
        default=AdRuleStatus.ACTIVE,
        verbose_name="规则状态",
    )

    shops = models.JSONField(
        default=list,
        verbose_name="适用店铺",
        help_text="店铺 profile_id 列表，如 [123, 456]",
    )

    ad_type = models.CharField(
        max_length=20,
        default="all",
        verbose_name="广告类型",
        help_text="all：不限 / manual：手动 / auto：自动",
    )

    effective_type = models.CharField(
        max_length=30,
        choices=EffectiveType.choices,
        default=EffectiveType.WITHIN_DAYS,
        verbose_name="生效周期类型",
    )

    effective_days_start = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效天数起始",
        help_text="effective_type 为 within_days/beyond_days 时使用，范围起点",
    )

    effective_days_end = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效天数结束",
        help_text="effective_type 为 within_days/beyond_days 时使用，范围终点",
    )

    effective_start_month = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效起始月",
        help_text="effective_type 为 date_range 时使用，1-12",
    )

    effective_start_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效起始日",
        help_text="effective_type 为 date_range 时使用，1-31",
    )

    effective_end_month = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效结束月",
        help_text="effective_type 为 date_range 时使用，1-12",
    )

    effective_end_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效结束日",
        help_text="effective_type 为 date_range 时使用，1-31",
    )

    categories = models.JSONField(
        default=list,
        verbose_name="归类列表",
    )

    unlimited_categories = models.BooleanField(
        default=False,
        verbose_name="归类不限",
    )

    managers = models.JSONField(
        default=list,
        verbose_name="负责人列表",
    )

    unlimited_managers = models.BooleanField(
        default=False,
        verbose_name="负责人不限",
    )

    tags = models.JSONField(
        default=list,
        verbose_name="标签列表",
    )

    unlimited_tags = models.BooleanField(
        default=False,
        verbose_name="标签不限",
    )

    auto_targeting_groups = models.JSONField(
        default=list,
        verbose_name="自动定位组",
        help_text="同类商品/紧密匹配/关联商品/宽泛匹配",
    )

    unlimited_auto_targeting = models.BooleanField(
        default=False,
        verbose_name="自动定位组不限",
    )

    comparison_target = models.CharField(
        max_length=50,
        choices=ComparisonTarget.choices,
        verbose_name="比对对象",
    )

    comparison_multi_targets = models.JSONField(
        default=list,
        verbose_name="投放多选列表",
        help_text="当 comparison_target 为 targeting 时，可多选 targeting / keyword / product_targeting",
    )

    condition_sets = models.JSONField(
        default=list,
        verbose_name="条件组",
        help_text="JSON 数组：每个元素包含 days（天数）和 conditions（条件列表）",
    )

    linked_time_rules = models.JSONField(
        default=list,
        verbose_name="关联分时规则",
        help_text="分时规则 ID 列表，命中后规则才生效",
    )

    linked_time_rules_exclude = models.JSONField(
        default=list,
        verbose_name="排除分时规则",
        help_text="分时规则 ID 列表，命中后规则不生效",
    )

    bid_action = models.JSONField(
        default=dict,
        verbose_name="竞价操作",
        help_text='{"type": "...", "value": 0, "limit": null}',
    )

    budget_action = models.JSONField(
        default=dict,
        verbose_name="预算操作",
        help_text='{"type": "...", "value": 0, "limit": null}',
    )

    other_action = models.JSONField(
        default=dict,
        verbose_name="其他操作",
        help_text='{"type": "pause"|"archive"|"", "notify": true}',
    )

    targeting_bid_actions = models.JSONField(
        default=list,
        verbose_name="投放竞价操作列表",
        help_text='Campaign AUTO/MANUAL 专属，每条包含 targetingGroups/conditionSets/bidAction',
    )

    negative_action = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name="否定操作",
        help_text="仅 comparison_target 为 search_terms 时有效",
    )

    add_keyword_action = models.CharField(
        max_length=50,
        default="",
        blank=True,
        verbose_name="关键词投放操作",
        help_text="仅 comparison_target 为 search_terms 时有效",
    )

    add_keyword_match_type = models.CharField(
        max_length=20,
        choices=AddKeywordMatchType.choices,
        default=AddKeywordMatchType.BROAD,
        verbose_name="关键词匹配方式",
    )

    add_keyword_bid_type = models.CharField(
        max_length=20,
        choices=AddKeywordBidType.choices,
        default=AddKeywordBidType.ACTUAL_CPC,
        verbose_name="关键词竞价方式",
    )

    add_keyword_max_bid = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="最高竞价",
    )

    add_keyword_fixed_bid = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="固定竞价",
    )

    creator = models.CharField(
        max_length=100,
        default="",
        verbose_name="创建人",
        help_text="创建该规则的用户名",
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
        db_table = "lx_ad_rule"
        verbose_name = "广告规则"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status_label = "启用" if self.status == AdRuleStatus.ACTIVE else "暂停"
        return f"LxAdRule<{self.id}> {self.name}（{status_label}）"
