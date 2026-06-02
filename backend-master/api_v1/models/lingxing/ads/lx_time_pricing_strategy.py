"""分时调价策略表（lx_time_pricing_strategy）。"""
from django.db import models


class StrategyType(models.TextChoices):
    """策略类型枚举。"""

    BIDDING_TIME = "bidding_time", "竞价分时"


class StrategyStatus(models.IntegerChoices):
    """策略模板状态枚举。"""

    PAUSED = 0, "暂停"
    ACTIVE = 1, "开启"


class BaseValueType(models.IntegerChoices):
    """基准值类型枚举。"""

    APPLY_AT_STRATEGY = 1, "应用策略时的值"
    FIXED = 2, "固定值"


class ExecutionResultType(models.IntegerChoices):
    """执行结果通知类型枚举。"""

    NOTIFY = 1, "通知"
    NO_NOTICE = 2, "不通知"


class LxTimePricingStrategy(models.Model):
    """分时调价策略表（领星 → 广告 → 分时调价策略）。"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="模板名称",
    )

    shops = models.JSONField(
        default=list,
        verbose_name="适用店铺",
        help_text="店铺标识列表，如 [\"US\", \"UK\"]",
    )

    status = models.IntegerField(
        choices=StrategyStatus.choices,
        default=StrategyStatus.ACTIVE,
        verbose_name="模板状态",
    )

    start_month = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效起始月（1-12）",
        help_text="null 表示不限",
    )

    start_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效起始日（1-31）",
        help_text="null 表示不限",
    )

    end_month = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效结束月（1-12）",
        help_text="null 表示不限",
    )

    end_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="生效结束日（1-31）",
        help_text="null 表示不限",
    )

    base_value_type = models.IntegerField(
        choices=BaseValueType.choices,
        default=BaseValueType.APPLY_AT_STRATEGY,
        verbose_name="基准值类型",
    )

    base_fixed_value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="固定基准值",
        help_text="仅当基准值类型为固定值时使用",
    )

    # 字段设置：{ "categories": [], "managers": [], "tags": [] }
    field_settings = models.JSONField(
        default=dict,
        verbose_name="字段设置",
        help_text="JSON 对象，包含 categories（归类列表）、managers（负责人列表）、tags（标签列表）",
    )

    # 分时模式：byDay / byWeek / calendar
    time_mode = models.CharField(
        max_length=20,
        default="byDay",
        verbose_name="分时模式",
        help_text="byDay：按天 / byWeek：按周 / calendar：日历模式",
    )

    # 分时设置数据：
    #   byDay / byWeek → { "segments": [{ "startTime", "endTime", "operateType", "operateValue", "limitValue", "dayOfWeek"(仅byWeek) }] }
    #   calendar       → { "grid": [[...7天], ...24小时] }
    time_settings = models.JSONField(
        default=dict,
        verbose_name="分时设置",
        help_text="时间段配置（segments）或日历网格（grid），结构由 time_mode 决定",
    )

    # 回调策略：
    #   { "type": "multiplier"|"fixed"|"previous"|"none", "multiplier": 1.0, "fixed": 0.5 }
    callback_settings = models.JSONField(
        default=dict,
        verbose_name="回调策略",
        help_text="失效回调配置：type + multiplier/fixed 值",
    )

    weight = models.IntegerField(
        default=1,
        verbose_name="权重",
        help_text="优先级排序，数值越大优先级越高",
    )

    execution_result = models.IntegerField(
        choices=ExecutionResultType.choices,
        default=ExecutionResultType.NO_NOTICE,
        verbose_name="执行结果通知",
    )

    type = models.CharField(
        max_length=50,
        choices=StrategyType.choices,
        default=StrategyType.BIDDING_TIME,
        verbose_name="策略类型",
    )

    creator = models.CharField(
        max_length=100,
        default="",
        verbose_name="创建人",
        help_text="创建该策略的用户名",
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
        db_table = "lx_time_pricing_strategy"
        verbose_name = "分时调价策略"
        verbose_name_plural = verbose_name
        ordering = ["-weight", "-created_at"]

    def __str__(self) -> str:
        status_label = "开启" if self.status == StrategyStatus.ACTIVE else "暂停"
        return f"LxTimePricingStrategy<{self.id}> {self.name}（{status_label}）"
