"""广告规则策略 — 规则组表（lx_ad_rule_group）。"""
from django.db import models


class LxAdRuleGroup(models.Model):
    """广告规则策略 — 规则组表（领星 → 广告 → 规则策略 → 规则组）。

    规则组按序号顺序执行内部规则，执行周期以天为单位。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="规则组名称",
    )

    execution_cycle = models.IntegerField(
        default=1,
        verbose_name="执行周期（天）",
        help_text="每 N 天执行一次，默认 1 表示每天执行",
    )

    rule_order = models.JSONField(
        default=list,
        verbose_name="规则 ID 有序列表",
        help_text="规则 ID 数组，如 [3, 7, 1]，按序执行",
    )

    creator = models.CharField(
        max_length=100,
        default="",
        verbose_name="创建人",
        help_text="创建该规则组的用户名",
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
        db_table = "lx_ad_rule_group"
        verbose_name = "规则组"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"LxAdRuleGroup<{self.id}> {self.name}"
