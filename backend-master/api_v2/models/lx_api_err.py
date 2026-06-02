"""领星 API 调用错误日志表（lx_api_err）。"""
from django.db import models


class LxApiErr(models.Model):
    """记录 middle.hanlis.cn API 调用失败的错误日志。"""

    task = models.CharField(
        max_length=100,
        default="",
        verbose_name="任务标识",
        help_text="如 bid_adjustment / time_pricing_callback",
    )

    task_name = models.CharField(
        max_length=200,
        default="",
        verbose_name="任务名",
        help_text="如 竞价调整 / 分时回调",
    )

    url = models.CharField(
        max_length=500,
        default="",
        verbose_name="请求接口",
    )

    method = models.CharField(
        max_length=10,
        default="POST",
        verbose_name="请求方法",
    )

    parameter = models.TextField(
        default="",
        blank=True,
        verbose_name="请求参数",
        help_text="请求体 JSON 文本（截断至 5000 字符）",
    )

    code = models.CharField(
        max_length=20,
        default="",
        verbose_name="状态/响应码",
        help_text="HTTP 状态码或 API 返回的 code 字段",
    )

    message = models.TextField(
        default="",
        blank=True,
        verbose_name="信息",
        help_text="错误信息或 API 返回的 message",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="发生时间",
    )

    class Meta:
        db_table = "lx_api_err"
        verbose_name = "领星API调用错误日志"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"LxApiErr<{self.task} {self.url}>"
