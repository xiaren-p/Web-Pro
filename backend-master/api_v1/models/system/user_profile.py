"""用户扩展信息模型。"""
from django.contrib.auth.models import User
from django.db import models

from api_v1.models._base import TimeStampedModel


class Gender(models.IntegerChoices):
    """性别枚举。"""

    UNKNOWN = 0, "保密"
    MALE = 1, "男"
    FEMALE = 2, "女"


class AdminLevel(models.IntegerChoices):
    """用户管理级别枚举：决定数据可见范围和 NC 管理员标志。"""

    COMPANY_ADMIN = 1, "公司管理员"
    DEPT_ADMIN = 2, "部门管理员"
    MEMBER = 3, "普通成员"


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

    position = models.ForeignKey(
        "Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="岗位",
        help_text="决定系统菜单权限，由管理员分配",
    )

    admin_level = models.IntegerField(
        choices=AdminLevel.choices,
        default=AdminLevel.MEMBER,
        verbose_name="管理级别",
        help_text="COMPANY_ADMIN=全数据+NC管理员；DEPT_ADMIN=本部门数据；MEMBER=仅本人数据",
    )

    extra_nc_groups = models.ManyToManyField(
        "NcGroup",
        blank=True,
        related_name="extra_users",
        verbose_name="额外 NC 群组",
        help_text="除部门群组外额外加入的 NC 群组（如项目组、公司共享等）",
    )

    nc_app_password = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="NC 应用密码（加密）",
        help_text="Fernet 密文存储，仅用于用户级 NC API 调用（如头像同步），不对外暴露",
    )

    class Meta:
        verbose_name = "用户扩展"
        verbose_name_plural = "用户扩展"

    def __str__(self) -> str:
        return f"UserProfile<{self.user_id}:{self.user.username}>"

    # ------------------------------------------------------------------ #
    #  NC 密码加解密辅助（Fernet AES-128-CBC + HMAC-SHA256）               #
    # ------------------------------------------------------------------ #

    def get_nc_password(self) -> str:
        """解密并返回 NC 应用密码明文。

        Returns:
            str: NC 密码明文；未设置或解密失败时返回空字符串。
        """
        if not self.nc_app_password:
            return ""
        from api_v1.utils.fernet_crypto import decrypt_value
        return decrypt_value(self.nc_app_password)

    def set_nc_password(self, plaintext: str) -> None:
        """加密存储 NC 应用密码（不自动 save，需调用方显式调用 .save()）。

        Args:
            plaintext (str): NC 密码明文；传空字符串表示清除密码。
        """
        from api_v1.utils.fernet_crypto import encrypt_value
        self.nc_app_password = encrypt_value(plaintext) if plaintext else ""

