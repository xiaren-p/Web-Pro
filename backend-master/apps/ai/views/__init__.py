"""AI 助手域 — 视图层。

所有 AI 对话、分组、应用相关接口。
视图实现由 Service 层支撑，本层仅做 HTTP 请求解析与响应包装。
"""

from apps.ai.views.chat_view import (
    start_chat,
    list_conversations,
    list_messages,
    delete_conversation,
    rename_conversation,
    pin_conversation,
    search_conversations,
    cancel_message,
)
from apps.ai.views.group_view import (
    list_groups,
    create_group,
    delete_group,
    rename_group,
    reorder_groups,
    move_conversation_to_group,
)
from apps.ai.views.stream_view import subscribe_message
from apps.ai.views.app_view import list_apps as list_ai_apps

__all__ = [
    "start_chat",
    "list_conversations",
    "list_messages",
    "delete_conversation",
    "rename_conversation",
    "pin_conversation",
    "search_conversations",
    "cancel_message",
    "list_groups",
    "create_group",
    "delete_group",
    "rename_group",
    "reorder_groups",
    "move_conversation_to_group",
    "subscribe_message",
    "list_ai_apps",
]
