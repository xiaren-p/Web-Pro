"""新增关键词 ID 列表字段：keyword_ids，记录 MANUAL 广告第四步的成功结果。"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0010_aduploadqueue_product_ad_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="aduploadqueue",
            name="keyword_ids",
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name="关键词 ID 列表",
            ),
        ),
    ]
