"""自动投放定向条款基础信息模型（lx_auto_targeting_info，managed=False）。"""
from django.db import models


class LxAutoTargetingInfo(models.Model):
    """自动投放定向条款基础信息表。

    每行对应一个自动定投组（紧密匹配 / 宽泛匹配 / 同类商品 / 关联商品），
    以 target_id + campaign_id + profile_id 三元唯一标识，不参与迁移。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    target_id = models.CharField(
        max_length=100,
        verbose_name="定向条款 ID",
    )

    targeting_text = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="自动定位组名称",
        help_text="紧密匹配 / 宽泛匹配 / 同类商品 / 关联商品",
    )

    ad_group_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="所属广告组 ID",
    )

    portfolio_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="所属广告组合 ID",
    )

    campaign_id = models.CharField(
        max_length=100,
        verbose_name="所属广告活动 ID",
    )

    profile_id = models.CharField(
        max_length=100,
        verbose_name="店铺 Profile ID",
    )

    state = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="有效状态",
        help_text="enabled / paused / archived",
    )

    service_status = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="服务状态·平台层面",
    )

    recommends = models.JSONField(
        null=True,
        blank=True,
        verbose_name="建议竞价信息",
        help_text="JSON: {suggested, rangeStart, rangeEnd, theme}",
    )

    bid = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="当前竞价",
    )

    bidding_strategy = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="竞价策略",
    )

    creation_date = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="创建时间（原始字符串）",
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=False,
        verbose_name="最后更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_auto_targeting_info"
        verbose_name = "自动投放定向条款信息"
        verbose_name_plural = "自动投放定向条款信息"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"LxAutoTargetingInfo<{self.target_id}>"
