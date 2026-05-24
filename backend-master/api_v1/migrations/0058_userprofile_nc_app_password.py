"""为 UserProfile 新增 nc_app_password 字段（Fernet 加密存储 NC 应用密码）。"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0057_seed_nc_folder_rmdir_button"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="nc_app_password",
            field=models.CharField(
                blank=True,
                default="",
                max_length=500,
                verbose_name="NC 应用密码（加密）",
                help_text="Fernet 密文存储，仅用于用户级 NC API 调用（如头像同步），不对外暴露",
            ),
        ),
    ]
