"""青龙 OpenAPI 配置预置迁移（0061_add_qinglong_config）。

在系统参数（Config）中预置以下三条青龙接入配置项（均为空值，由管理员在参数配置页填写）：
  - QINGLONG_URL          青龙面板地址
  - QINGLONG_CLIENT_ID    OpenAPI client_id
  - QINGLONG_CLIENT_SECRET OpenAPI client_secret（PASSWORD 类型，加密存储）
"""
from django.db import migrations


def add_qinglong_configs(apps, schema_editor):
    """预置青龙 OpenAPI 接入配置到 Config 表（若键已存在则跳过）。"""
    Config = apps.get_model("api_v1", "Config")
    entries = [
        (
            "QINGLONG_URL",
            "TEXT",
            "",
            "青龙面板地址，如 http://192.168.0.10:5700",
        ),
        (
            "QINGLONG_CLIENT_ID",
            "TEXT",
            "",
            "青龙 OpenAPI client_id（在青龙面板 → 系统设置 → 应用设置 中生成）",
        ),
        (
            "QINGLONG_CLIENT_SECRET",
            "PASSWORD",
            "",
            "青龙 OpenAPI client_secret（加密存储，在青龙面板 → 系统设置 → 应用设置 中生成）",
        ),
    ]
    for key, config_type, value, remark in entries:
        Config.objects.get_or_create(
            key=key,
            defaults={
                "value": value,
                "config_type": config_type,
                "remark": remark,
                "status": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0060_merge_20260529"),
    ]

    operations = [
        migrations.RunPython(
            add_qinglong_configs,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
