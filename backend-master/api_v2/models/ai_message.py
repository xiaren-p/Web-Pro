"""AI 对话消息表（ai_message）。"""

import uuid

from django.db import models

from api_v2.models.ai_conversation import AiConversation


class MessageRole(models.TextChoices):
    """消息发送方角色枚举。"""

    USER = 'user', '用户'
    ASSISTANT = 'assistant', 'AI 助手'


class MessageType(models.TextChoices):
    """消息内容类型枚举。"""

    TEXT = 'text', '文本'
    PLAN = 'plan', '计划提案'


class MessageStatus(models.TextChoices):
    """消息生成状态枚举。

    业务语义：
        PENDING：消息已创建但 Celery 任务尚未开始处理。
        STREAMING：Celery 任务正在流式接收 Dify 输出并向 Redis 频道广播。
        DONE：消息生成完毕，content 字段已落库齐全。
        FAILED：生成过程中抛出异常，error_msg 字段记录原因。
        CANCELLED：用户主动取消（通过 /messages/<id>/cancel/ 端点）。
    """

    PENDING = 'pending', '待处理'
    STREAMING = 'streaming', '生成中'
    DONE = 'done', '已完成'
    FAILED = 'failed', '失败'
    CANCELLED = 'cancelled', '已取消'


class AiMessage(models.Model):
    """AI 对话单条消息记录。

    设计说明：
        采用"边生成边落库"策略，Celery 任务在流式接收 Dify chunk 时定期将累积内容写入 ``content`` 字段，
        从而保证用户刷新 / 关闭 / 重新打开页面后仍能拉到最新进度。
        ``raw_plan_json`` 仅在 message_type=plan 时使用，存放未翻译前的原始 Plan Schema 以便审计回放。
        ``status`` 字段是订阅视图判断"是否还在生成 / 是否需要继续监听 Redis 频道"的核心依据。

    双 ID 设计：
        ``id`` 整数主键，仅内部 join / 外键 / Celery 任务参数使用（int 序列化更轻）；
        ``public_id`` UUID，对外暴露给前端与 SSE URL，避免泄露内部计数。
    """

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name='对外公开 ID',
    )

    conversation = models.ForeignKey(
        AiConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='所属会话',
    )

    role = models.CharField(
        max_length=16,
        choices=MessageRole.choices,
        verbose_name='消息角色',
    )

    message_type = models.CharField(
        max_length=16,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        verbose_name='消息类型',
    )

    status = models.CharField(
        max_length=16,
        choices=MessageStatus.choices,
        default=MessageStatus.PENDING,
        db_index=True,
        verbose_name='生成状态',
    )

    content = models.TextField(
        blank=True,
        default='',
        verbose_name='消息正文',
    )

    raw_plan_json = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Plan 原始 Schema',
    )

    dify_message_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='Dify 平台消息 ID',
    )

    task_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Celery Task ID',
    )

    error_msg = models.TextField(
        blank=True,
        default='',
        verbose_name='错误信息',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='创建时间',
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='最后更新时间',
    )

    class Meta:
        managed = True
        db_table = 'ai_message'
        verbose_name = 'AI 对话消息'
        verbose_name_plural = 'AI 对话消息'
        ordering = ['conversation_id', 'created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self) -> str:
        return f"AiMessage<{self.pk} {self.role} {self.status}>"
