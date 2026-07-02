"""数据采集节点配置模型。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class CrawlerConf(TimeStampedModel):
    """数据采集节点配置。

    记录可公开访问的爬取节点配置（开放接口，无需认证）。
    前端使用字段：server_name / node / ip / status / order_num。
    """

    server_name = models.CharField(
        max_length=200,
        verbose_name="服务器名称",
    )

    node = models.CharField(
        max_length=200,
        verbose_name="节点标识",
    )

    ip = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="IP 地址",
    )

    status = models.IntegerField(
        default=1,
        verbose_name="状态",
    )

    order_num = models.IntegerField(
        default=0,
        verbose_name="排序号",
    )

    class Meta:
        verbose_name = "数据采集节点"
        verbose_name_plural = "数据采集节点"
        ordering = ("order_num", "id")

