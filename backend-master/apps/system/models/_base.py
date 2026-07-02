"""
时间戳抽象基类（跨板块复用）
"""
from django.db import models


class TimeStampedModel(models.Model):
    """时间戳抽象基类：自动维护创建/更新时间"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
