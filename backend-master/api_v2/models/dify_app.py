"""Dify 应用配置表（dify_app）。"""

import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class DifyAppMode(models.TextChoices):
    """Dify 应用类型枚举。

    业务语义：
        CHATFLOW: 对应 Dify 模板里的 "聊天助手 / Chatflow"，提示词驱动的对话流。
        AGENT:    对应 Dify 的 "Agent" 应用，模型可自主调用工具。
        WORKFLOW: 对应 Dify 的 "Workflow" 应用，非对话型一次性输入输出（首期暂不接入）。
    """

    CHATFLOW = 'chatflow', '聊天流'
    AGENT = 'agent', '智能体'
    WORKFLOW = 'workflow', '工作流'


class DifyAppManager(models.Manager):
    """DifyApp 自定义 Manager，提供"取默认应用"的便捷方法。"""

    def get_default(self) -> 'DifyApp':
        """获取系统默认 Dify 应用。

        查找顺序：
            1. ``is_default=True`` 且 ``is_active=True`` 的第一条
            2. 退化：取 ``is_active=True`` 中 ``sort_order`` 最小的第一条

        Returns:
            DifyApp: 默认应用实例。

        Raises:
            DifyApp.DoesNotExist: 数据库中没有任何可用应用。
        """
        active_qs = self.filter(is_active=True)
        default = active_qs.filter(is_default=True).first()
        if default is not None:
            return default

        fallback = active_qs.order_by('sort_order', 'id').first()
        if fallback is None:
            raise self.model.DoesNotExist('数据库中无任何 is_active=True 的 DifyApp 记录')
        return fallback


class DifyApp(models.Model):
    """Dify 平台应用配置表。

    一条记录代表项目内可调用的一个 Dify 应用（聊天助手 / Agent 等），
    存放该应用的 base URL、加密后的 API Key、展示元数据，
    供 ``DifyClient`` 与前端"应用切换器"使用。

    安全约束：
        ``api_key_encrypted`` 使用 ``settings.FERNET_SECRET_KEY`` Fernet 对称加密后存储，
        DB 中永不出现明文 sk-xxx。读写均通过 ``encrypt_api_key`` / ``decrypt_api_key`` 方法封装。
    """

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name='对外公开 ID',
    )

    code = models.CharField(
        max_length=40,
        unique=True,
        verbose_name='应用代码',
        help_text='英文 + 下划线小写代码，前端切换 chip 时携带此值，例：default / listing_image',
    )

    name = models.CharField(
        max_length=80,
        verbose_name='应用名称',
        help_text='用户在 chip 上看到的中文名称，例："通用助手" / "Listing 图片生成"',
    )

    description = models.TextField(
        blank=True,
        default='',
        verbose_name='应用描述',
        help_text='下拉菜单中展示给用户的辅助说明文字',
    )

    icon = models.CharField(
        max_length=10,
        default='💬',
        verbose_name='应用图标',
        help_text='单个 emoji 字符，前端 chip 与列表头像渲染使用',
    )

    mode = models.CharField(
        max_length=20,
        choices=DifyAppMode.choices,
        default=DifyAppMode.CHATFLOW,
        verbose_name='应用类型',
    )

    api_base = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Dify Base URL',
        help_text='留空时回退到 settings.DIFY_API_BASE',
    )

    api_key_encrypted = models.BinaryField(
        verbose_name='加密后的 API Key',
        help_text='通过 cryptography.Fernet 加密的 sk-xxx 密钥，禁止在任何日志/响应中暴露',
    )

    default_inputs = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='默认 inputs 模板',
        help_text='调用 Dify 时合并到 inputs 的预置变量，例：{"thinking_mode": "off"}',
    )

    sort_order = models.IntegerField(
        default=0,
        db_index=True,
        verbose_name='展示顺序',
        help_text='前端下拉菜单按此值升序排列',
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用',
        help_text='False 表示该应用不在前端切换器中展示',
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name='是否为默认应用',
        help_text='前端首次打开时自动选中的应用；同一时刻应仅有一条为 True',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='最后更新时间',
    )

    objects = DifyAppManager()

    class Meta:
        managed = True
        db_table = 'dify_app'
        verbose_name = 'Dify 应用配置'
        verbose_name_plural = 'Dify 应用配置'
        ordering = ['sort_order', 'id']

    def __str__(self) -> str:
        return f'DifyApp<{self.pk} {self.code} {self.name}>'

    # ── 加密 / 解密辅助 ──────────────────────────────────────────

    @staticmethod
    def _get_cipher() -> Fernet:
        """构造 Fernet 实例。

        Returns:
            Fernet: 已加载项目密钥的对称加密器。

        Raises:
            RuntimeError: settings.FERNET_SECRET_KEY 未配置时抛出。
        """
        secret = getattr(settings, 'FERNET_SECRET_KEY', '') or ''
        if not secret:
            raise RuntimeError(
                '[DifyApp] settings.FERNET_SECRET_KEY 未配置，无法处理 Dify API Key 加密'
            )
        return Fernet(secret.encode() if isinstance(secret, str) else secret)

    @classmethod
    def encrypt_api_key(cls, plaintext: str) -> bytes:
        """把明文 API Key 加密为可入库的 bytes。

        Args:
            plaintext (str): 明文 sk-xxx 密钥。

        Returns:
            bytes: Fernet 加密后的密文，可直接写入 ``api_key_encrypted``。

        Raises:
            ValueError: plaintext 为空。
        """
        if not plaintext:
            raise ValueError('API Key 明文不能为空')
        cipher = cls._get_cipher()
        return cipher.encrypt(plaintext.encode('utf-8'))

    def decrypt_api_key(self) -> str:
        """从数据库读出密文并解密为明文 sk-xxx。

        Returns:
            str: 明文 API Key，仅在 DifyClient 内部使用，禁止落日志。
        """
        cipher = self._get_cipher()
        raw = bytes(self.api_key_encrypted) if self.api_key_encrypted else b''
        if not raw:
            raise ValueError(f'DifyApp<{self.code}> 的 api_key_encrypted 为空')
        return cipher.decrypt(raw).decode('utf-8')

    def resolve_api_base(self) -> str:
        """解析最终生效的 Dify base URL。

        Returns:
            str: 优先 ``self.api_base``；为空时回退 ``settings.DIFY_API_BASE``。
        """
        if self.api_base:
            return self.api_base.rstrip('/')
        fallback = getattr(settings, 'DIFY_API_BASE', '') or ''
        return fallback.rstrip('/')
