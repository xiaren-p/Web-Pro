"""广告上传队列序列化器（ad_upload_queue_serializer）。

职责：将 AdUploadQueue 模型序列化为前端直接可用的数据结构；
枚举翻译与状态标签在本层完成，前端无需二次加工。
"""

from rest_framework import serializers

from api_v2.models.ad_upload_queue import AdParseStatus, AdUploadQueue


class AdUploadQueueSerializer(serializers.ModelSerializer):
    """广告上传队列响应序列化器。

    parse_status_label 由后端完成枚举翻译，前端直接渲染，
    遵循"数据出口最终成形"原则。
    """

    parse_status_label = serializers.SerializerMethodField()
    ad_type_label = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = AdUploadQueue
        fields = [
            "id",
            "campaign_name",
            "shop",
            "country",
            "ad_type",
            "ad_type_label",
            "params",
            "step_ids",
            "parse_status",
            "parse_status_label",
            "msg",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = fields

    def get_parse_status_label(self, obj: AdUploadQueue) -> str:
        """返回状态的中文标签。

        Args:
            obj (AdUploadQueue): 队列记录实例。

        Returns:
            str: "队列中" / "失败" / "成功"。
        """
        from api_v2.models.ad_upload_queue import AdParseStatus
        label_map = {
            AdParseStatus.PENDING: "队列中",
            AdParseStatus.SUCCESS: "成功",
            AdParseStatus.FAILED: "失败",
            AdParseStatus.ANOMALY: "异常",
        }
        return label_map.get(obj.parse_status, "未知")

    def get_ad_type_label(self, obj: AdUploadQueue) -> str:
        """返回广告类型的中文标签（手动 / 自动）。

        Args:
            obj (AdUploadQueue): 队列记录实例。

        Returns:
            str: "手动" 或 "自动"。
        """
        return "手动" if obj.ad_type == "manual" else "自动"

    def get_created_by_username(self, obj: AdUploadQueue) -> str:
        """返回创建用户的用户名；未关联用户时返回空字符串。

        Args:
            obj (AdUploadQueue): 队列记录实例。

        Returns:
            str: 用户名，如 "admin"；无关联时返回 ""。
        """
        if obj.created_by_id is None:
            return ""
        return obj.created_by.username if obj.created_by else ""


class AdBulkDeleteSerializer(serializers.Serializer):
    """批量删除队列记录请求体序列化器。"""

    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        help_text="要删除的队列记录 ID 列表",
    )
