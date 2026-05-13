"""亮礿用户列表镜像模型（lx_user_list，managed=False）。"""
from django.db import models


class LxUserList(models.Model):
    """用户列表数据表。"""

    uid = models.BigIntegerField(
        primary_key=True,
        verbose_name="主键 UID",
    )

    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="名字",
    )

    name_zh = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="中文名字",
    )

    has_rule = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="是否有规则",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="系统更新时间",
    )

    class Meta:
        managed = False
        db_table = "lx_user_list"
        verbose_name = "用户列表"
        verbose_name_plural = "用户列表"

