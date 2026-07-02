"""对外 API 请求日志表（api_v2_api_request_log）。

记录系统主动发出的所有外部 HTTP 请求，含请求时间、URL、方式、传参方式、参数、响应结果与作用描述。
"""

from django.db import models


class HttpMethod(models.TextChoices):
    """HTTP 请求方式枚举。"""

    GET = "GET", "GET"
    POST = "POST", "POST"
    PUT = "PUT", "PUT"
    PATCH = "PATCH", "PATCH"
    DELETE = "DELETE", "DELETE"


class ParamType(models.TextChoices):
    """请求传参方式枚举。"""

    FORM = "form", "表单（form-encoded）"
    JSON = "json", "JSON 体"
    QUERY = "query", "查询字符串"


class ApiRequestLog(models.Model):
    """对外 API 请求日志表。"""

    requested_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="请求时间",
    )

    url = models.CharField(
        max_length=500,
        verbose_name="请求 URL",
    )

    method = models.CharField(
        max_length=10,
        choices=HttpMethod.choices,
        default=HttpMethod.POST,
        verbose_name="请求方式",
    )

    param_type = models.CharField(
        max_length=10,
        choices=ParamType.choices,
        default=ParamType.FORM,
        verbose_name="传参方式",
    )

    request_headers = models.JSONField(
        default=dict,
        verbose_name="请求头",
    )

    request_params = models.JSONField(
        default=dict,
        verbose_name="请求参数",
    )

    response_body = models.JSONField(
        default=dict,
        verbose_name="响应结果",
    )

    purpose = models.CharField(
        max_length=255,
        default="",
        verbose_name="作用描述",
    )

    class Meta:
        db_table = "api_v2_api_request_log"
        verbose_name = "API 请求日志"
        verbose_name_plural = "API 请求日志"
        ordering = ["-requested_at"]

    def __str__(self) -> str:
        return f"ApiRequestLog<{self.pk}> [{self.method}] {self.url}"
