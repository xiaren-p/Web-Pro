"""添加广告上传队列竞价字段：每日预算、广告组默认竞价及自动定向四类竞价。"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0007_simplify_ad_upload_queue"),
    ]

    operations = [
        migrations.AddField(
            model_name="aduploadqueue",
            name="daily_budget",
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                max_digits=10,
                verbose_name="每日预算",
            ),
        ),
        migrations.AddField(
            model_name="aduploadqueue",
            name="default_bid",
            field=models.DecimalField(
                decimal_places=2,
                default=0.12,
                max_digits=10,
                verbose_name="广告组默认竞价",
            ),
        ),
        migrations.AddField(
            model_name="aduploadqueue",
            name="close_match_bid",
            field=models.DecimalField(
                decimal_places=2,
                default=0.12,
                max_digits=10,
                verbose_name="紧密匹配竞价",
            ),
        ),
        migrations.AddField(
            model_name="aduploadqueue",
            name="loose_match_bid",
            field=models.DecimalField(
                decimal_places=2,
                default=0.10,
                max_digits=10,
                verbose_name="同类匹配竞价",
            ),
        ),
        migrations.AddField(
            model_name="aduploadqueue",
            name="substitutes_bid",
            field=models.DecimalField(
                decimal_places=2,
                default=0.10,
                max_digits=10,
                verbose_name="宽泛匹配竞价",
            ),
        ),
        migrations.AddField(
            model_name="aduploadqueue",
            name="complements_bid",
            field=models.DecimalField(
                decimal_places=2,
                default=0.10,
                max_digits=10,
                verbose_name="关联匹配竞价",
            ),
        ),
    ]
