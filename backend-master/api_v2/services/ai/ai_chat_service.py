"""AI 对话编排服务（ai_chat_service）。

承担"接收用户问题 → 创建会话 / 消息 → 入队 Celery 任务"的编排职责。
本服务被视图层调用（瘦 Controller / 胖 Service 原则），不直接持有 Web 请求对象。
真正的流式 AI 调用在 Celery 任务里执行，本服务只负责快速建表 + 入队后立刻返回。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Optional, Union

from django.contrib.auth.models import User
from django.db import transaction

from api_v2.models.ai_conversation import AiConversation
from api_v2.models.ai_message import AiMessage, MessageRole, MessageStatus, MessageType

logger = logging.getLogger(__name__)


@dataclass
class ChatStartResult:
    """``AiChatService.start_chat`` 的返回结构。

    所有 ID 字段均为对外公开 UUID 字符串（``public_id``），
    内部整数主键不暴露给视图 / 前端。

    Attributes:
        conversation_id (str): 会话 public_id（UUID）。
        user_message_id (str): 用户消息 public_id（UUID）。
        assistant_message_id (str): 待生成的 AI 消息 public_id（UUID），
            前端用此 ID 订阅 SSE 频道。
        celery_task_id (str): Celery 任务 ID。
    """

    conversation_id: str
    user_message_id: str
    assistant_message_id: str
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
        conversation_id: Optional[Union[uuid.UUID, str]] = None,
        app_code: Optional[str] = None,
        inputs: Optional[dict] = None,
    ) -> ChatStartResult:
        """提交一轮对话，创建消息记录并派发 Celery 任务。

        编排步骤：
            1. 复用或新建 AiConversation；新建时绑定到指定的 Dify 应用并以 query 前 30 字作为标题
            2. 立刻落一条 user 角色消息（status=DONE，因用户内容已确定）
            3. 落一条 assistant 角色消息（status=PENDING，等待 Celery 填充）
            4. 派发 ``run_ai_chat_task`` 到 parallel_queue，携带 dify_app_id
            5. 把 task_id 回写到 assistant message，方便后续取消

        Args:
            user (User): 当前登录用户。
            query (str): 用户提问原文。
            conversation_id (Optional[uuid.UUID | str]): 续接已有会话的 ``public_id``；
                为 None 时新建会话。
            app_code (Optional[str]): 前端选定的 Dify 应用 code。
                新建会话时必填（兜底为默认应用）；续接会话时忽略（沿用会话已绑定的应用，
                因 Dify 的 conversation_id 不可跨应用复用）。
            inputs (Optional[dict]): Dify 工作流变量，由前端业务上下文带入。
                会与所选 ``DifyApp.default_inputs`` 合并（用户传入优先）。

        Returns:
            ChatStartResult: 创建的会话 / 消息 / 任务标识（UUID 字符串）。

        Raises:
            ValueError: 当 conversation_id 不属于当前用户、或 app_code 对应应用
                不存在 / 未启用时抛出。
        """
        # 延迟导入避免 Celery 任务模块在 Django 启动期被反向引用造成循环依赖
        from api_v2.tasks.ai_chat_task import run_ai_chat_task

        with transaction.atomic():
            conversation = self._resolve_conversation(user, conversation_id, query, app_code)

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

        # 合并应用预置 inputs 与本次请求 inputs：本次 inputs 优先
        merged_inputs: dict = {}
        if conversation.dify_app and conversation.dify_app.default_inputs:
            merged_inputs.update(conversation.dify_app.default_inputs)
        if inputs:
            merged_inputs.update(inputs)

        # 入队动作放在事务外：
        # 防止 Celery worker 抢先执行任务时事务尚未提交，从而读到不存在的消息行
        # Celery 任务参数仍传内部整数主键 —— 任务体只与 ORM 交互，无需暴露 UUID
        async_result = run_ai_chat_task.delay(
            conversation_id=conversation.id,
            user_id=user.id,
            assistant_message_id=assistant_message.id,
            query=query,
            dify_conversation_id=conversation.dify_conversation_id,
            dify_app_id=conversation.dify_app_id,
            inputs=merged_inputs,
        )

        AiMessage.objects.filter(pk=assistant_message.pk).update(task_id=async_result.id)

        logger.info(
            '[AiChatService][start_chat] 任务已派发: user=%s conv_pk=%s app=%s assistant_pk=%s task=%s',
            user.id,
            conversation.id,
            conversation.dify_app.code if conversation.dify_app else '<none>',
            assistant_message.id,
            async_result.id,
        )

        return ChatStartResult(
            conversation_id=str(conversation.public_id),
            user_message_id=str(user_message.public_id),
            assistant_message_id=str(assistant_message.public_id),
            celery_task_id=async_result.id,
        )

    def _resolve_conversation(
        self,
        user: User,
        conversation_id: Optional[Union[uuid.UUID, str]],
        query: str,
        app_code: Optional[str] = None,
    ) -> AiConversation:
        """获取或新建对话会话。

        Args:
            user (User): 当前用户。
            conversation_id (Optional[uuid.UUID | str]): 已有会话的 ``public_id``；
                为 None 时新建。
            query (str): 用户提问，新建会话时用作默认标题。
            app_code (Optional[str]): 新建会话时要绑定的 Dify 应用 code；
                为 None 或对应应用不存在 / 已停用时回退到 ``DifyApp.objects.get_default()``。
                续接会话时此参数被忽略。

        Returns:
            AiConversation: 已存在或新建的会话实例。

        Raises:
            ValueError: 当指定的 conversation_id 不存在或不属于当前用户时抛出。
        """
        # 延迟导入避免模型层启动期循环依赖
        from api_v2.models.dify_app import DifyApp

        if conversation_id is None:
            target_app: Optional[DifyApp] = None
            if app_code:
                target_app = DifyApp.objects.filter(code=app_code, is_active=True).first()
            if target_app is None:
                # 找不到 / 未启用 → 回退到系统默认应用，避免阻断对话
                try:
                    target_app = DifyApp.objects.get_default()
                except DifyApp.DoesNotExist:
                    target_app = None

            return AiConversation.objects.create(
                user=user,
                title=self._make_default_title(query),
                dify_app=target_app,
            )

        try:
            conversation = AiConversation.objects.select_related('dify_app').get(
                public_id=conversation_id,
                user=user,
            )
        except AiConversation.DoesNotExist as exc:
            raise ValueError(f'会话不存在或无权访问: id={conversation_id}') from exc

        # 续接会话忽略前端 app_code（Dify 的 conversation_id 不能跨应用复用）
        if app_code and conversation.dify_app and conversation.dify_app.code != app_code:
            logger.warning(
                '[AiChatService][_resolve_conversation] 前端切换应用但续接的会话已绑定别的应用: '
                'conv=%s bound_app=%s requested_app=%s（忽略请求，使用 bound_app）',
                conversation.public_id,
                conversation.dify_app.code,
                app_code,
            )

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
