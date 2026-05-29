"""简化广告上传队列表：删除 campaign_status / campaign_response 字段，
parse_status 统一承载全流程状态（0=失败 1=队列中 2=成功）。
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0006_merge_20260529"),
    ]

    operations = [
        # 删除 campaign_response 字段
        migrations.RemoveField(
            model_name="aduploadqueue",
            name="campaign_response",
        ),
        # 删除 campaign_status 字段
        migrations.RemoveField(
            model_name="aduploadqueue",
            name="campaign_status",
        ),
        # 更新 parse_status：choices 变更（0=失败/1=队列中/2=成功），default 改为 1
        migrations.AlterField(
            model_name="aduploadqueue",
            name="parse_status",
            field=models.IntegerField(
                choices=[(0, "失败"), (1, "队列中"), (2, "成功")],
                db_index=True,
                default=1,
                verbose_name="状态",
            ),
        ),
    ]
