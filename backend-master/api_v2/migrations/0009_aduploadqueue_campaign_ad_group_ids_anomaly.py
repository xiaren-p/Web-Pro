"""新增广告队列步骤结果字段：campaign_id、ad_group_id，并增加 ANOMALY=3 状态选项。"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0008_add_bidding_fields_to_aduploadqueue"),
    ]

    operations = [
        migrations.AddField(
            model_name="aduploadqueue",
            name="campaign_id",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
                verbose_name="广告活动 ID",
            ),
        ),
        migrations.AddField(
            model_name="aduploadqueue",
            name="ad_group_id",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
                verbose_name="广告组 ID",
            ),
        ),
        migrations.AlterField(
            model_name="aduploadqueue",
            name="parse_status",
            field=models.IntegerField(
                choices=[
                    (0, "失败"),
                    (1, "队列中"),
                    (2, "成功"),
                    (3, "异常"),
                ],
                db_index=True,
                default=1,
                verbose_name="状态",
            ),
        ),
    ]
