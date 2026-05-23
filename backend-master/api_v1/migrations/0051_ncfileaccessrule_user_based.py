# Generated migration: switch NcFileAccessRule from group-based to user-based ACL.
# Old data is cleared since group-based rules are incompatible with the new schema.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_v1', '0050_alter_ncfileaccessrule_nc_path_alter_ncgroup_dept_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. 清除旧的群组规则数据（与新 user-based 模型不兼容）
        migrations.RunSQL(
            sql="DELETE FROM api_v1_ncfileaccessrule;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # 2. 移除旧的 unique_together 约束（nc_group + nc_path）
        migrations.AlterUniqueTogether(
            name='ncfileaccessrule',
            unique_together=set(),
        ),
        # 3. 删除 is_group_folder 字段
        migrations.RemoveField(
            model_name='ncfileaccessrule',
            name='is_group_folder',
        ),
        # 4. 删除旧的 nc_group FK
        migrations.RemoveField(
            model_name='ncfileaccessrule',
            name='nc_group',
        ),
        # 5. 新增 user FK
        migrations.AddField(
            model_name='ncfileaccessrule',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='nc_file_rules',
                to=settings.AUTH_USER_MODEL,
                verbose_name='用户',
            ),
        ),
        # 6. 重建 unique_together（user + nc_path）
        migrations.AlterUniqueTogether(
            name='ncfileaccessrule',
            unique_together={('user', 'nc_path')},
        ),
        # 7. 更新 ordering（已在 Meta 中定义，migration 中仅需 AlterModelOptions）
        migrations.AlterModelOptions(
            name='ncfileaccessrule',
            options={
                'ordering': ('user_id', 'nc_path'),
                'verbose_name': 'NC 文件访问规则',
                'verbose_name_plural': 'NC 文件访问规则',
            },
        ),
    ]
