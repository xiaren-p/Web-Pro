"""为 NcGroup 新增 folder_id 字段，用于存储 Group Folder 创建后的 NC folder ID。"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_v1', '0045_remove_role_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='ncgroup',
            name='folder_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name='NC Group Folder ID',
                help_text='create_group_folder 返回的 folder id，用于后续 grant_group_folder 授权',
            ),
        ),
    ]
