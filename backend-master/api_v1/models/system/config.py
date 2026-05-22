"""系统参数配置模型。"""
import logging

from django.db import models

from api_v1.models._base import TimeStampedModel

logger = logging.getLogger(__name__)


class ConfigType(models.TextChoices):
    """参数值类型枚举。"""

    TEXT = "TEXT", "明文"
    PASSWORD = "PASSWORD", "加密存储"


class Config(TimeStampedModel):
    """系统参数配置。PASSWORD 类型的 value 在数据库中以 Fernet 密文存储。"""

    key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="参数键",
    )

    value = models.TextField(
        blank=True,
        default="",
        verbose_name="参数值",
        help_text="PASSWORD 类型时存储 Fernet 密文，请勿直接修改",
    )

    remark = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="备注",
    )

    status = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    config_type = models.CharField(
        max_length=10,
        choices=ConfigType.choices,
        default=ConfigType.TEXT,
        verbose_name="值类型",
    )

    class Meta:
        verbose_name = "系统参数"
        verbose_name_plural = "系统参数"

    def __str__(self) -> str:
        return self.key

    def get_plaintext_value(self) -> str:
        """返回参数的明文值。

        PASSWORD 类型自动解密后返回；TEXT 类型直接返回原值。
        解密失败时记录警告并返回空字符串。

        Returns:
            str: 明文参数值。
        """
        if self.config_type != ConfigType.PASSWORD:
            return self.value or ""
        from api_v1.utils.fernet_crypto import decrypt_value
        return decrypt_value(self.value or "")

    def set_plaintext_value(self, plaintext: str) -> None:
        """设置参数值，PASSWORD 类型自动加密后存入 value 字段。

        调用后需手动 .save() 持久化。

        Args:
            plaintext (str): 明文参数值。
        """
        if self.config_type != ConfigType.PASSWORD:
            self.value = plaintext
        else:
            from api_v1.utils.fernet_crypto import encrypt_value
            self.value = encrypt_value(plaintext) if plaintext else ""

