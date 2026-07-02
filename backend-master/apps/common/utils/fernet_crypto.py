"""Fernet 对称加密工具：用于 Config 模型 PASSWORD 类型值的加密存储。

安全说明：
  - 密钥来自 settings.FERNET_SECRET_KEY（环境变量注入，绝不硬编码）。
  - 使用 cryptography.fernet.Fernet（AES-128-CBC + HMAC-SHA256），防篡改。
  - 解密失败不抛异常，记录警告后返回空字符串，防止接口崩溃。
"""
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """获取 Fernet 实例。密钥来自 settings.FERNET_SECRET_KEY。

    Returns:
        Fernet: 加密实例。

    Raises:
        RuntimeError: 若 FERNET_SECRET_KEY 未配置。
    """
    key: str = getattr(settings, "FERNET_SECRET_KEY", "") or ""
    if not key:
        raise RuntimeError(
            "[fernet_crypto] FERNET_SECRET_KEY 未配置，"
            "请在 .env 中添加该环境变量。"
            "生成命令：python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    raw: bytes = key.encode() if isinstance(key, str) else key
    return Fernet(raw)


def encrypt_value(plaintext: str) -> str:
    """对明文字符串加密，返回 Fernet token（URL-safe base64 字符串）。

    Args:
        plaintext (str): 待加密的明文。

    Returns:
        str: 加密后的密文字符串；若输入为空则原样返回。
    """
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """解密 Fernet 密文字符串，返回明文。

    解密失败（密钥轮换/数据损坏）时记录警告并返回空字符串，不抛异常。

    Args:
        ciphertext (str): 待解密的密文。

    Returns:
        str: 解密后的明文；失败时返回空字符串。
    """
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning(
            "[fernet_crypto] [decrypt_value] Token 无效，密钥可能已轮换或数据已损坏。"
        )
        return ""
    except Exception as exc:
        logger.error(
            "[fernet_crypto] [decrypt_value] 解密异常：%s",
            str(exc),
            exc_info=True,
        )
        return ""
