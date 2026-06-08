"""领星 SP 广告活动信息序列化器。"""
from rest_framework import serializers

from api_v1.models import LxSpCampaign


class LxSpCampaignSerializer(serializers.ModelSerializer):
    """SP 广告活动信息全字段序列化器。"""

    class Meta:
        model = LxSpCampaign
        fields = "__all__"
