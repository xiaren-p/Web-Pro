"""新增广告投放 ID 列表字段：product_ad_ids，记录每条队列第三步的成功结果。"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0009_aduploadqueue_campaign_ad_group_ids_anomaly"),
    ]

    operations = [
        migrations.AddField(
            model_name="aduploadqueue",
            name="product_ad_ids",
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name="广告投放 ID 列表",
            ),
        ),
    ]
