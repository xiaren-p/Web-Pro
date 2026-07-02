"""领星用户表（lx_user，managed=False）。"""
from django.db import models


class UserStatus(models.IntegerChoices):
    """用户状态枚举。"""

    DISABLED = 0, "禁用"
    NORMAL = 1, "正常"


class IsMaster(models.IntegerChoices):
    """是否主账号枚举。"""

    SUB = 0, "子账号"
    MASTER = 1, "主账号"


class LxUser(models.Model):
    """领星用户表（基础数据 → 用户）。"""

    uid = models.IntegerField(
        primary_key=True,
        verbose_name="用户 ID",
    )

    realname = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="姓名",
    )

    username = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="用户名",
    )

    mobile = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="电话",
    )

    email = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="邮箱",
    )

    login_num = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name="登录次数",
    )

    last_login_time = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="最近登录时间",
    )

    last_login_ip = models.CharField(
        max_length=45,
        null=True,
        blank=True,
        verbose_name="最近登录 IP",
    )

    status = models.IntegerField(
        choices=UserStatus.choices,
        default=UserStatus.NORMAL,
        verbose_name="状态",
    )

    create_time = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="创建时间",
    )

    role = models.TextField(
        null=True,
        blank=True,
        verbose_name="角色（逗号分隔）",
    )

    seller = models.TextField(
        null=True,
        blank=True,
        verbose_name="店铺权限（逗号分隔）",
    )

    is_master = models.IntegerField(
        choices=IsMaster.choices,
        default=IsMaster.SUB,
        verbose_name="是否主账号",
    )

    class Meta:
        managed = False
        db_table = "lx_user"
        verbose_name = "领星用户"
        verbose_name_plural = "领星用户"
        ordering = ["uid"]

    def __str__(self) -> str:
        return f"LxUser<{self.uid} - {self.realname or self.username}>"
