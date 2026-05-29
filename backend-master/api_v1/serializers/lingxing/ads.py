"""领星广告活动信息序列化器。"""
from rest_framework import serializers
from api_v1.models import LxCampaignInfo


class LxCampaignInfoSerializer(serializers.ModelSerializer):
    """领星广告活动信息全字段序列化器。"""

    class Meta:
        model = LxCampaignInfo
        fields = "__all__"
