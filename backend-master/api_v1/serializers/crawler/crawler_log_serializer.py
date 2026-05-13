"""爬虫日志序列化器。"""
from rest_framework import serializers
from api_v1.models import CrawlerLog


class CrawlerLogSerializer(serializers.ModelSerializer):
    """爬虫日志读写序列化器，对 level 进行别名归一化处理。"""

    # level 允许预定义的日志级别，兼容常见别名（如 "warning" -> "warn"）
    level = serializers.ChoiceField(
        choices=["debug", "info", "warn", "warning", "error"], required=False
    )

    class Meta:
        model = CrawlerLog
        fields = [
            "id", "module", "content", "level", "elapsed_ms",
            "operator", "ip", "user_agent", "created_at",
        ]

    def validate_level(self, value):
        # 归一化常见同义词到内部统一集合
        if not value:
            return "info"
        v = str(value).strip().lower()
        mapping = {
            "warning": "warn",
            "warn": "warn",
            "error": "error",
            "err": "error",
            "info": "info",
            "debug": "debug",
        }
        return mapping.get(v, "info")

    def validate_elapsed_ms(self, value):
        try:
            return int(value or 0)
        except Exception:
            raise serializers.ValidationError("elapsed_ms must be integer")
