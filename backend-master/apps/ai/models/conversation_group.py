"""AI 对话分组表（ai_conversation_group）。"""

import uuid

from django.contrib.auth.models import User
from django.db import models


class AiConversationGroup(models.Model):
    """AI 对话用户自定义分组。

    设计：
        每个用户可创建多个分组（如"采购"、"广告优化"），用于把会话归类便于查找。
        分组与会话是"一对多"关系：一条会话最多属于一个分组（或不属于任何分组）。
        ``order`` 字段控制分组在侧栏的展示顺序（数字小的在上）。

    双 ID 设计：
        ``id`` 整数主键内部使用；``public_id`` UUID 对外暴露。
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
        related_name='ai_conversation_groups',
        verbose_name='所属用户',
    )

    name = models.CharField(
        max_length=80,
        verbose_name='分组名称',
    )

    order = models.IntegerField(
        default=0,
        db_index=True,
        verbose_name='展示顺序',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='最后更新时间',
    )

    class Meta:
        managed = True
        db_table = 'ai_conversation_group'
        verbose_name = 'AI 对话分组'
        verbose_name_plural = 'AI 对话分组'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['user', 'order']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='uniq_ai_group_user_name',
            ),
        ]

    def __str__(self) -> str:
        """返回模型的字符串表示。"""
        return f'AiConversationGroup<{self.pk} {self.name}>'
