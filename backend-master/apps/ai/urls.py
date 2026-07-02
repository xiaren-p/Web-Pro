"""AI 助手域 — URL 路由。"""

from django.urls import path

from apps.ai.views import (
    start_chat,
    list_conversations,
    list_messages,
    delete_conversation,
    rename_conversation,
    pin_conversation,
    search_conversations,
    cancel_message,
    list_groups,
    create_group,
    delete_group,
    rename_group,
    reorder_groups,
    move_conversation_to_group,
    subscribe_message,
    list_ai_apps,
)

urlpatterns = [
    # 聊天
    path("chat/", start_chat, name="ai_chat_start"),
    path("stream/<uuid:public_id>/", subscribe_message, name="ai_stream_subscribe"),
    path("conversations/", list_conversations, name="ai_conversations_list"),
    path("conversations/search/", search_conversations, name="ai_conversations_search"),
    path("conversations/<uuid:public_id>/", delete_conversation, name="ai_conversations_delete"),
    path("conversations/<uuid:public_id>/rename/", rename_conversation, name="ai_conversations_rename"),
    path("conversations/<uuid:public_id>/pin/", pin_conversation, name="ai_conversations_pin"),
    path("conversations/<uuid:public_id>/messages/", list_messages, name="ai_conversations_messages"),
    path("conversations/<uuid:public_id>/move/", move_conversation_to_group, name="ai_conversations_move"),
    path("messages/<uuid:public_id>/cancel/", cancel_message, name="ai_message_cancel"),
    # 分组
    path("groups/", list_groups, name="ai_groups_list"),
    path("groups/create/", create_group, name="ai_groups_create"),
    path("groups/reorder/", reorder_groups, name="ai_groups_reorder"),
    path("groups/<uuid:public_id>/", delete_group, name="ai_groups_delete"),
    path("groups/<uuid:public_id>/rename/", rename_group, name="ai_groups_rename"),
    # 应用
    path("apps/", list_ai_apps, name="ai_apps_list"),
]
