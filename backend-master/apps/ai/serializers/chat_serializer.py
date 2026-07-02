"""AI 对话相关 Serializer（ai_chat_serializer）。"""

from rest_framework import serializers

from apps.ai.models.conversation import AiConversation
from apps.ai.models.conversation_group import AiConversationGroup
from apps.ai.models.message import AiMessage, MessageRole, MessageStatus, MessageType
from apps.ai.models.dify_app import DifyApp


class AiChatRequestSerializer(serializers.Serializer):
    """``POST /api/v2/ai/chat/`` 入参校验。"""

    query = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=5000,
        trim_whitespace=True,
        help_text='用户提问原文',
    )
    conversation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text='续接会话的对外 UUID；新建对话时省略',
    )
    app_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=40,
        help_text='前端选择的 Dify 应用 code；新建会话时按此切换 agent，续接会话时被忽略（沿用会话已绑定的应用）',
    )
    inputs = serializers.DictField(
        required=False,
        allow_null=True,
        help_text='Dify 工作流变量，由前端业务上下文按需注入',
    )


class AiConversationGroupSerializer(serializers.ModelSerializer):
    """会话分组响应结构。"""

    id = serializers.UUIDField(source='public_id', read_only=True)

    class Meta:
        model = AiConversationGroup
        fields = ['id', 'name', 'order', 'created_at', 'updated_at']
        read_only_fields = fields


class AiConversationSerializer(serializers.ModelSerializer):
    """会话列表的最小响应结构。

    对外把 ``public_id`` 渲染为 ``id``；分组关联以 ``group_id`` 形式给出对应分组的 UUID；
    Dify 应用归属以 ``app_code`` / ``app_name`` / ``app_icon`` 三字段成形输出，前端零翻译。
    ``pinned_at`` 不为空表示已置顶。
    """

    id = serializers.UUIDField(source='public_id', read_only=True)
    group_id = serializers.UUIDField(source='group.public_id', read_only=True, allow_null=True)
    app_code = serializers.CharField(source='dify_app.code', read_only=True, allow_null=True)
    app_name = serializers.CharField(source='dify_app.name', read_only=True, allow_null=True)
    app_icon = serializers.CharField(source='dify_app.icon', read_only=True, allow_null=True)
    is_pinned = serializers.SerializerMethodField()

    class Meta:
        model = AiConversation
        fields = [
            'id',
            'title',
            'dify_conversation_id',
            'group_id',
            'app_code',
            'app_name',
            'app_icon',
            'is_pinned',
            'pinned_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_is_pinned(self, obj: AiConversation) -> bool:
        return obj.pinned_at is not None


class AiMessageSerializer(serializers.ModelSerializer):
    """消息详情响应结构（含枚举中文标签）。"""

    id = serializers.UUIDField(source='public_id', read_only=True)
    conversation_id = serializers.UUIDField(source='conversation.public_id', read_only=True)
    role_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    message_type_label = serializers.SerializerMethodField()

    class Meta:
        model = AiMessage
        fields = [
            'id',
            'conversation_id',
            'role',
            'role_label',
            'message_type',
            'message_type_label',
            'status',
            'status_label',
            'content',
            'raw_plan_json',
            'error_msg',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_role_label(self, obj: AiMessage) -> str:
        return MessageRole(obj.role).label

    def get_status_label(self, obj: AiMessage) -> str:
        return MessageStatus(obj.status).label

    def get_message_type_label(self, obj: AiMessage) -> str:
        return MessageType(obj.message_type).label


class AiSearchHitSerializer(serializers.Serializer):
    """搜索结果命中条目（含会话信息 + 命中片段）。"""

    conversation_id = serializers.UUIDField(read_only=True)
    conversation_title = serializers.CharField(read_only=True)
    message_id = serializers.UUIDField(read_only=True, allow_null=True)
    role = serializers.CharField(read_only=True, allow_null=True)
    snippet = serializers.CharField(read_only=True)
    matched_at = serializers.DateTimeField(read_only=True)


class DifyAppSerializer(serializers.ModelSerializer):
    """Dify 应用列表响应结构（仅暴露前端切换器需要的字段，不返回密钥/base URL）。"""

    id = serializers.UUIDField(source='public_id', read_only=True)

    class Meta:
        model = DifyApp
        fields = [
            'id',
            'code',
            'name',
            'description',
            'icon',
            'mode',
            'is_default',
            'sort_order',
        ]
        read_only_fields = fields
