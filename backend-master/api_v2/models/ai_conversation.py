"""AI 对话会话表（ai_conversation）。"""

from django.contrib.auth.models import User
from django.db import models


class AiConversation(models.Model):
    """AI 助手对话会话表。

    一条记录代表用户在侧栏发起的一次"对话窗口"，可包含多轮 user / assistant 消息。
    通过 ``dify_conversation_id`` 维系与 Dify 平台的上下文记忆，使 LLM 能跨轮次记住上下文；
    本表自身负责会话列表展示、跨设备同步、合规审计的业务留痕能力。
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name='所属用户',
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
