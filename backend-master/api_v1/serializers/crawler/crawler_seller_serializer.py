"""爬虫卖家账号序列化器。"""
from rest_framework import serializers
from api_v1.models import CrawlerSellerAccount


class CrawlerSellerSerializer(serializers.ModelSerializer):
    """爬虫卖家账号序列化器。"""

    class Meta:
        model = CrawlerSellerAccount
        fields = ["id", "username", "password", "status", "order_num", "created_at", "updated_at"]
