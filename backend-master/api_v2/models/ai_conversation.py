"""AI 对话会话表（ai_conversation）。"""

import uuid

from django.contrib.auth.models import User
from django.db import models

from api_v2.models.ai_conversation_group import AiConversationGroup
from api_v2.models.dify_app import DifyApp


class AiConversation(models.Model):
    """AI 助手对话会话表。

    一条记录代表用户在侧栏发起的一次"对话窗口"，可包含多轮 user / assistant 消息。
    通过 ``dify_conversation_id`` 维系与 Dify 平台的上下文记忆，使 LLM 能跨轮次记住上下文；
    本表自身负责会话列表展示、跨设备同步、合规审计的业务留痕能力。

    双 ID 设计：
        ``id`` 整数主键，仅在内部 join / 外键中使用；
        ``public_id`` UUID，对外暴露给前端与 URL，避免泄露内部计数与业务量。

    分组与置顶：
        ``group`` 可选外键，若为空表示"未分组"；
        ``pinned_at`` 不为空表示置顶，置顶按其值倒序排列后再展示其余非置顶会话。

    Dify 应用绑定：
        ``dify_app`` 标识此会话归属哪个 Dify 应用（聊天助手 / Agent）。
        新建会话时锁定到选定 app，后续轮次必须沿用同一 app —— 因 Dify 的
        ``conversation_id`` 本身不可跨应用复用。``on_delete=PROTECT`` 防止误删
        应用导致历史会话失联。
    """

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name='对外公开 ID',
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name='所属用户',
    )

    group = models.ForeignKey(
        AiConversationGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        verbose_name='所属分组',
    )

    dify_app = models.ForeignKey(
        DifyApp,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='conversations',
        verbose_name='所属 Dify 应用',
    )

    pinned_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='置顶时间',
    )

    dify_conversation_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        db_index=True,
        verbose_name='Dify 平台会话 ID',
    )

    title = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='会话标题',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='创建时间',
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='最后活跃时间',
    )

    class Meta:
        managed = True
        db_table = 'ai_conversation'
        verbose_name = 'AI 对话会话'
        verbose_name_plural = 'AI 对话会话'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
        ]

    def __str__(self) -> str:
        return f"AiConversation<{self.pk} {self.title or '(无标题)'}>"
