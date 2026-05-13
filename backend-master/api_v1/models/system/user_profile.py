"""用户扩展信息模型。"""
from django.contrib.auth.models import User
from django.db import models

from api_v1.models._base import TimeStampedModel
from api_v1.models.system.role import Role


class Gender(models.IntegerChoices):
    """性别枚举。"""

    UNKNOWN = 0, "保密"
    MALE = 1, "男"
    FEMALE = 2, "女"


class UserProfile(TimeStampedModel):
    """用户扩展信息（不替换内置 User，避免迁移复杂度）。"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="用户",
    )

    nickname = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="昵称",
    )

    mobile = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="手机号",
    )

    avatar = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="头像地址",
    )

    cloud_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="云账号标识",
        help_text="第三方 Seafile 返回的 account email/ID，后续同步删除使用",
    )

    dept = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="所属部门",
    )

    gender = models.IntegerField(
        choices=Gender.choices,
        default=Gender.UNKNOWN,
        verbose_name="性别",
    )

    roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name="users",
        verbose_name="角色列表",
    )

    class Meta:
        verbose_name = "用户扩展"
        verbose_name_plural = "用户扩展"

