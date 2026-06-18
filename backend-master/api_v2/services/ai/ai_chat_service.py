"""AI 对话编排服务（ai_chat_service）。

承担"接收用户问题 → 创建会话 / 消息 → 入队 Celery 任务"的编排职责。
本服务被视图层调用（瘦 Controller / 胖 Service 原则），不直接持有 Web 请求对象。
真正的流式 AI 调用在 Celery 任务里执行，本服务只负责快速建表 + 入队后立刻返回。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction

from api_v2.models.ai_conversation import AiConversation
from api_v2.models.ai_message import AiMessage, MessageRole, MessageStatus, MessageType

logger = logging.getLogger(__name__)


@dataclass
class ChatStartResult:
    """``AiChatService.start_chat`` 的返回结构。

    Attributes:
        conversation_id (int): 业务库 AiConversation 主键。
        user_message_id (int): 用户提问消息主键。
        assistant_message_id (int): 待生成的 AI 回复消息主键，前端用此 ID 订阅 SSE 频道。
        celery_task_id (str): Celery 任务 ID，便于后续取消或追踪。
    """

    conversation_id: int
    user_message_id: int
    assistant_message_id: int
    celery_task_id: str


class AiChatService:
    """AI 对话编排服务。

    采用类形态而非纯函数集合的原因：
        将来扩展"会话标题自动生成"、"敏感词预检"、"用户配额校验"等横切逻辑时，
        类内部可方便组合 helper 方法；当前只放 ``start_chat`` 一个对外入口。
    """

    def start_chat(
        self,
        user: User,
        query: str,
        conversation_id: Optional[int] = None,
        inputs: Optional[dict] = None,
    ) -> ChatStartResult:
        """提交一轮对话，创建消息记录并派发 Celery 任务。

        编排步骤：
            1. 复用或新建 AiConversation；新建时以 query 前 30 字作为标题
            2. 立刻落一条 user 角色消息（status=DONE，因用户内容已确定）
            3. 落一条 assistant 角色消息（status=PENDING，等待 Celery 填充）
            4. 派发 ``run_ai_chat_task`` 到 parallel_queue
            5. 把 task_id 回写到 assistant message，方便后续取消

        Args:
            user (User): 当前登录用户。
            query (str): 用户提问原文。
            conversation_id (Optional[int]): 续接已有会话的 ID；为 None 时新建。
            inputs (Optional[dict]): Dify 工作流变量，由前端业务上下文带入。

        Returns:
            ChatStartResult: 创建的会话 / 消息 / 任务标识，前端凭此订阅 SSE。

        Raises:
            ValueError: 当 conversation_id 不属于当前用户时抛出，防止越权。
        """
        # 延迟导入避免 Celery 任务模块在 Django 启动期被反向引用造成循环依赖
        from api_v2.tasks.ai_chat_task import run_ai_chat_task

        with transaction.atomic():
            conversation = self._resolve_conversation(user, conversation_id, query)

            user_message = AiMessage.objects.create(
                conversation=conversation,
                role=MessageRole.USER,
                message_type=MessageType.TEXT,
                status=MessageStatus.DONE,
                content=query,
            )

            assistant_message = AiMessage.objects.create(
                conversation=conversation,
                role=MessageRole.ASSISTANT,
                message_type=MessageType.TEXT,
                status=MessageStatus.PENDING,
                content='',
            )

            # 触发 conversation.updated_at 刷新（auto_now 在 .save() 才生效）
            conversation.save(update_fields=['updated_at'])

        # 入队动作放在事务外：
        # 防止 Celery worker 抢先执行任务时事务尚未提交，从而读到不存在的消息行
        async_result = run_ai_chat_task.delay(
            conversation_id=conversation.id,
            user_id=user.id,
            assistant_message_id=assistant_message.id,
            query=query,
            dify_conversation_id=conversation.dify_conversation_id,
            inputs=inputs or {},
        )

        AiMessage.objects.filter(id=assistant_message.id).update(task_id=async_result.id)

        logger.info(
            '[AiChatService][start_chat] 任务已派发: user=%s conv=%s assistant_msg=%s task=%s',
            user.id,
            conversation.id,
            assistant_message.id,
            async_result.id,
        )

        return ChatStartResult(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            celery_task_id=async_result.id,
        )

    def _resolve_conversation(
        self,
        user: User,
        conversation_id: Optional[int],
        query: str,
    ) -> AiConversation:
        """获取或新建对话会话。

        Args:
            user (User): 当前用户。
            conversation_id (Optional[int]): 已有会话 ID；为 None 时新建。
            query (str): 用户提问，新建会话时用作默认标题。

        Returns:
            AiConversation: 已存在或新建的会话实例。

        Raises:
            ValueError: 当指定的 conversation_id 不存在或不属于当前用户时抛出。
        """
        if conversation_id is None:
            return AiConversation.objects.create(
                user=user,
                title=self._make_default_title(query),
            )

        try:
            conversation = AiConversation.objects.get(id=conversation_id, user=user)
        except AiConversation.DoesNotExist as exc:
            raise ValueError(f'会话不存在或无权访问: id={conversation_id}') from exc

        return conversation

    @staticmethod
    def _make_default_title(query: str) -> str:
        """从用户首条提问截取默认标题。

        Args:
            query (str): 用户提问原文。

        Returns:
            str: 长度不超过 30 的标题字符串。
        """
        cleaned = query.strip().replace('\n', ' ')
        if len(cleaned) <= 30:
            return cleaned
        return cleaned[:30] + '…'
