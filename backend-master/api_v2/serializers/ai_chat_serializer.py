"""AI 对话相关 Serializer（ai_chat_serializer）。"""

from rest_framework import serializers

from api_v2.models.ai_conversation import AiConversation
from api_v2.models.ai_message import AiMessage, MessageRole, MessageStatus, MessageType


class AiChatRequestSerializer(serializers.Serializer):
    """``POST /api/v2/ai/chat/`` 入参校验。

    职责：
        - 校验 query 必填且非空
        - 校验 conversation_id 是数字（具体所有权由 service 层校验，避免序列化层做查询）
        - 接收可选 inputs 透传给 Dify 工作流变量
    """

    query = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=5000,
        trim_whitespace=True,
        help_text='用户提问原文',
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='续接会话的 ID；新建对话时省略',
    )
    inputs = serializers.DictField(
        required=False,
        allow_null=True,
        help_text='Dify 工作流变量，由前端业务上下文按需注入',
    )


class AiConversationSerializer(serializers.ModelSerializer):
    """会话列表的最小响应结构。"""

    class Meta:
        model = AiConversation
        fields = ['id', 'title', 'dify_conversation_id', 'created_at', 'updated_at']
        read_only_fields = fields


class AiMessageSerializer(serializers.ModelSerializer):
    """消息详情响应结构（含枚举中文标签）。

    遵守"数据出口最终成形"：枚举翻译在后端完成，前端拿到 ``role_label`` / ``status_label`` 直接展示。
    """

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
