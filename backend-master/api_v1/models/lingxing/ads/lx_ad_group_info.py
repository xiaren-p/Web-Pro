"""广告组基础信息模型（lx_ad_group_info，managed=False）。"""
from django.db import models


class LxAdGroupInfo(models.Model):
    """广告组基础信息表。

    ORM 只读取数据，不参与迁移。
    campaign_id + profile_id 构成业务复合查询主键，
    防止不同店铺出现相同 campaign_id 时数据错位。
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name="自增主键",
    )

    ad_group_id = models.CharField(
        max_length=100,
        verbose_name="广告组 ID",
    )

    name = models.CharField(
        max_length=255,
        default="",
        verbose_name="广告组名称",
    )

    state = models.CharField(
        max_length=50,
        default="",
        verbose_name="有效状态",
        help_text="enabled / paused / archived",
    )

    service_status = models.CharField(
        max_length=100,
        default="",
        verbose_name="服务状态·平台层面",
    )

    portfolio_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="所属广告组合 ID",
    )

    default_bid = models.FloatField(
        null=True,
        blank=True,
        verbose_name="默认竞价金额",
    )

    count_product_ads = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="关联商品广告数量",
    )

    campaign_id = models.CharField(
        max_length=100,
        default="",
        verbose_name="所属广告活动 ID",
    )

    profile_id = models.CharField(
        max_length=100,
        default="",
        verbose_name="店铺 Profile ID",
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
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_ad_group_info"
        verbose_name = "广告组基础信息表"
        verbose_name_plural = "广告组基础信息表"
        unique_together = (("ad_group_id", "campaign_id", "profile_id"),)

