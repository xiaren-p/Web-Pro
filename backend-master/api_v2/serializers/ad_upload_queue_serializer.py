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

    class Meta:
        model = AdUploadQueue
        fields = [
            "id",
            "campaign_name",
            "shop",
            "country",
            "ad_type",
            "skus",
            "keywords",
            "parse_status",
            "parse_status_label",
            "msg",
            "created_at",
        ]
        read_only_fields = fields

    def get_parse_status_label(self, obj: AdUploadQueue) -> str:
        """返回解析状态的中文标签（队列中 / 失败）。

        Args:
            obj (AdUploadQueue): 队列记录实例。

        Returns:
            str: "队列中" 或 "失败"。
        """
        return "队列中" if obj.parse_status == AdParseStatus.SUCCESS else "失败"


class AdBulkDeleteSerializer(serializers.Serializer):
    """批量删除队列记录请求体序列化器。"""

    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        help_text="要删除的队列记录 ID 列表",
    )
