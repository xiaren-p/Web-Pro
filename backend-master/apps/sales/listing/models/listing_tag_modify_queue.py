"""Listing 商品标签修改队列表（listing_tag_modify_queue）。

记录 Listing 页面对 single / batch 标签操作时每个 MSKU 的新增/删除标签差异。
"""
from django.db import models


class ModifyActionChoices(models.TextChoices):
    """标签修改动作枚举。"""

    ADD = "add", "新增"
    REMOVE = "remove", "移除"


class ListingTagModifyQueue(models.Model):
    """Listing 商品标签修改队列。

    前端每次 upsert_labels 时，计算新旧 global_tags 差异并写入此表，
    供异步任务消费以追加/移除标签到外部系统。
    """

    action = models.CharField(
        max_length=10,
        choices=ModifyActionChoices.choices,
        verbose_name="修改类型",
    )

    msku = models.CharField(
        max_length=200,
        default="",
        verbose_name="MSKU",
    )

    sid = models.IntegerField(
        verbose_name="店铺 ID",
    )

    tag_ids = models.JSONField(
        default=list,
        verbose_name="标签 ID 数组",
        help_text="新增/移除的 globalTagId 数组",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        db_table = "listing_tag_modify_queue"
        verbose_name = "Listing 商品标签修改队列"
        verbose_name_plural = "Listing 商品标签修改队列"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["msku", "sid"], name="ltmq_msku_sid_idx"),
        ]

    def __str__(self) -> str:
        return f"ListingTagModifyQueue<{self.action} msku={self.msku} sid={self.sid} tags={self.tag_ids}>"
