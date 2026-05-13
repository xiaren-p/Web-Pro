"""爬虫节点配置序列化器。"""
from rest_framework import serializers
from api_v1.models import CrawlerConf


class CrawlerConfSerializer(serializers.ModelSerializer):
    """爬虫服务器节点配置序列化器。"""

    class Meta:
        model = CrawlerConf
        fields = ["id", "server_name", "node", "ip", "status", "order_num", "created_at", "updated_at"]
