# Generated 2026-05-29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0003_aduploadqueue_campaign_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiRequestLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "requested_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        verbose_name="请求时间",
                    ),
                ),
                (
                    "url",
                    models.CharField(
                        max_length=500,
                        verbose_name="请求 URL",
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("GET", "GET"),
                            ("POST", "POST"),
                            ("PUT", "PUT"),
                            ("PATCH", "PATCH"),
                            ("DELETE", "DELETE"),
                        ],
                        default="POST",
                        max_length=10,
                        verbose_name="请求方式",
                    ),
                ),
                (
                    "param_type",
                    models.CharField(
                        choices=[
                            ("form", "表单（form-encoded）"),
                            ("json", "JSON 体"),
                            ("query", "查询字符串"),
                        ],
                        default="form",
                        max_length=10,
                        verbose_name="传参方式",
                    ),
                ),
                (
                    "request_headers",
                    models.JSONField(
                        default=dict,
                        verbose_name="请求头",
                    ),
                ),
                (
                    "request_params",
                    models.JSONField(
                        default=dict,
                        verbose_name="请求参数",
                    ),
                ),
                (
                    "response_body",
                    models.JSONField(
                        default=dict,
                        verbose_name="响应结果",
                    ),
                ),
                (
                    "purpose",
                    models.CharField(
                        default="",
                        max_length=255,
                        verbose_name="作用描述",
                    ),
                ),
            ],
            options={
                "verbose_name": "API 请求日志",
                "verbose_name_plural": "API 请求日志",
                "db_table": "api_v2_api_request_log",
                "ordering": ["-requested_at"],
            },
        ),
    ]
