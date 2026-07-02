"""AI 对话流式生成 Celery 任务（ai_chat_task，运行于 parallel_queue）。"""

import logging

from celery import shared_task
from django.utils import timezone

from apps.ai.models.conversation import AiConversation
from apps.ai.models.message import AiMessage, MessageStatus, MessageType
from apps.ai.services.dify_client import DifyClient
from apps.ai.services.plan_translator import PlanTranslator
from apps.ai.utils.redis_channel import (
    EVENT_DONE,
    EVENT_ERROR,
    EVENT_MESSAGE_META,
    EVENT_PLAN,
    EVENT_TOKEN,
    get_redis_client,
    publish_event,
)

logger = logging.getLogger(__name__)


# 累积多少字符触发一次 DB 落盘：
# 每帧立刻写库会把 AiMessage 改成"高频 UPDATE 单行"，对 MySQL 不友好；
# 完全等任务结束才写又会丢"刷新页面"场景的中间进度。
# 64 字符是一个较合理的折中：约每秒 1~2 次 DB 写入。
_DB_FLUSH_INTERVAL_CHARS = 64


@shared_task(
    bind=True,
    name='apps.ai.tasks.chat_task.run_ai_chat_task',
    max_retries=0,
    soft_time_limit=840,
    time_limit=900,
)
def run_ai_chat_task(
    self,
    conversation_id: int,
    user_id: int,
    assistant_message_id: int,
    query: str,
    dify_conversation_id: str = '',
    dify_app_id: int | None = None,
    inputs: dict | None = None,
    **kwargs,
) -> dict:
    """流式调用 Dify 对话接口、边生成边落库、边广播 Redis 频道。

    本任务是 Plan Mode 架构的"重活承担者"——浏览器端关闭也不影响本任务持续运行，
    用户回到页面后可基于消息 ID 重新订阅 Redis 频道继续接收（或从 DB 拉历史回放）。

    Args:
        conversation_id (int): AiConversation 主键。
        user_id (int): 触发用户 ID，作为 Dify ``user`` 参数实现配额隔离。
        assistant_message_id (int): 待填充的 AI 回复消息主键。
        query (str): 用户本轮提问。
        dify_conversation_id (str): Dify 平台会话 ID；新会话传空字符串。
        dify_app_id (int | None): 该会话所属 ``DifyApp`` 主键。
            为 None 时回退到 ``DifyApp.objects.get_default()``，兼容历史会话。
        inputs (dict | None): Dify 工作流变量。

    Returns:
        dict: 任务执行摘要，包含 message_id / final_status / chars_written 等。

    Raises:
        Exception: Dify 调用层异常会抛出，Celery 自动落入失败状态；
            本函数捕获后会先把消息状态置 FAILED 并广播 error 事件再 re-raise。
    """
    # 延迟导入避免循环依赖
    from apps.ai.models.dify_app import DifyApp

    redis_client = get_redis_client()
    dify_app = None
    if dify_app_id is not None:
        dify_app = DifyApp.objects.filter(pk=dify_app_id, is_active=True).first()
    # dify_app 为 None 时 DifyClient 自动回退到默认应用
    dify_client = DifyClient(app=dify_app)
    plan_translator = PlanTranslator()

    accumulated: list[str] = []
    last_flush_pos = 0
    final_dify_conversation_id = dify_conversation_id
    final_dify_message_id = ''

    # 起手就把消息状态置为 STREAMING + 广播 message_meta，前端可立即展示加载占位
    AiMessage.objects.filter(id=assistant_message_id).update(
        status=MessageStatus.STREAMING,
    )
    publish_event(
        redis_client,
        assistant_message_id,
        EVENT_MESSAGE_META,
        {
            'conversation_id': conversation_id,
            'message_id': assistant_message_id,
        },
    )

    try:
        for chunk in dify_client.stream_chat(
            query=query,
            user_identifier=str(user_id),
            conversation_id=dify_conversation_id,
            inputs=inputs or {},
        ):
            # 缓存稳定字段（首帧后即可填）
            if chunk.conversation_id and not final_dify_conversation_id:
                final_dify_conversation_id = chunk.conversation_id
            if chunk.message_id:
                final_dify_message_id = chunk.message_id

            if chunk.event == 'message' and chunk.answer_delta:
                # 累积文本 + 推送 token 事件
                accumulated.append(chunk.answer_delta)
                publish_event(
                    redis_client,
                    assistant_message_id,
                    EVENT_TOKEN,
                    {'text': chunk.answer_delta},
                )

                # 阈值触发 DB 落盘
                current_total_len = sum(len(s) for s in accumulated)
                if current_total_len - last_flush_pos >= _DB_FLUSH_INTERVAL_CHARS:
                    AiMessage.objects.filter(id=assistant_message_id).update(
                        content=''.join(accumulated),
                    )
                    last_flush_pos = current_total_len

        # 流结束：最后一次 DB 落盘 + 解析 Plan
        full_text = ''.join(accumulated)
        plan_text = plan_translator.extract_plan_text(full_text)
        plan_payload = plan_translator.translate(plan_text) if plan_text else None

        update_fields = {
            'content': full_text,
            'status': MessageStatus.DONE,
            'updated_at': timezone.now(),
        }
        if plan_payload is not None:
            update_fields['message_type'] = MessageType.PLAN
            update_fields['raw_plan_json'] = plan_payload
        if final_dify_message_id:
            update_fields['dify_message_id'] = final_dify_message_id

        AiMessage.objects.filter(id=assistant_message_id).update(**update_fields)

        # 同步 Dify 会话 ID 回写到 conversation 表
        if final_dify_conversation_id:
            AiConversation.objects.filter(id=conversation_id).update(
                dify_conversation_id=final_dify_conversation_id,
            )

        # 推送结尾事件：plan 优先（前端把消息切换为卡片渲染），随后必发 done
        if plan_payload is not None:
            publish_event(redis_client, assistant_message_id, EVENT_PLAN, plan_payload)
        publish_event(redis_client, assistant_message_id, EVENT_DONE, {})

        logger.info(
            '[run_ai_chat_task] 完成: msg=%s chars=%s has_plan=%s',
            assistant_message_id,
            len(full_text),
            plan_payload is not None,
        )

        return {
            'message_id': assistant_message_id,
            'final_status': MessageStatus.DONE,
            'chars_written': len(full_text),
            'has_plan': plan_payload is not None,
        }

    except Exception as exc:
        logger.error(
            '[run_ai_chat_task] 失败: msg=%s err=%s',
            assistant_message_id,
            str(exc),
            exc_info=True,
        )

        # 先把已生成内容尽量保留，再标记失败
        partial = ''.join(accumulated)
        AiMessage.objects.filter(id=assistant_message_id).update(
            content=partial,
            status=MessageStatus.FAILED,
            error_msg=str(exc)[:500],
        )

        # 广播错误事件，让正在订阅的前端能够立刻感知
        publish_event(
            redis_client,
            assistant_message_id,
            EVENT_ERROR,
            {'code': 'AI_CHAT_FAILED', 'message': str(exc)[:200]},
        )
        publish_event(redis_client, assistant_message_id, EVENT_DONE, {})

        raise
