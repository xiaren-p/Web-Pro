"""爬虫日志序列化器。"""
from rest_framework import serializers
from apps.crawler.models import CrawlerLog


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
        """归一化日志级别字段。

将 warning/err 等常见别名映射为内部统一集合。

Args:
    value (str): 原始日志级别。

Returns:
    str: 归一化后的日志级别，空值返回 "info"。
"""
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
        """校验并转换耗时字段为整数。

Args:
    value: 原始耗时值。

Returns:
    int: 耗时毫秒数，空值返回 0。

Raises:
    serializers.ValidationError: 无法转为整数时抛出。
"""
        try:
            return int(value or 0)
        except Exception:
            raise serializers.ValidationError("elapsed_ms must be integer")
