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

    class Meta:
        model = AdUploadQueue
        fields = [
            "id",
            "campaign_name",
            "shop",
            "country",
            "ad_type",
            "ad_type_label",
            "skus",
            "keywords",
            "parse_status",
            "parse_status_label",
            "msg",
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


class AdBulkDeleteSerializer(serializers.Serializer):
    """批量删除队列记录请求体序列化器。"""

    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        help_text="要删除的队列记录 ID 列表",
    )
