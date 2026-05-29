# Generated 2026-05-29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0002_aduploadqueue"),
    ]

    operations = [
        migrations.AddField(
            model_name="aduploadqueue",
            name="campaign_status",
            field=models.IntegerField(
                choices=[(0, "待提交"), (1, "提交成功"), (2, "提交失败")],
                default=0,
                db_index=True,
                verbose_name="API 提交状态",
            ),
        ),
        migrations.AddField(
            model_name="aduploadqueue",
            name="campaign_response",
            field=models.JSONField(
                default=dict,
                verbose_name="API 响应数据",
            ),
        ),
    ]
