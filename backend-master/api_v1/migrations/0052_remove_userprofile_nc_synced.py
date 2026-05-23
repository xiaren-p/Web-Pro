"""移除 UserProfile.nc_synced 字段（该字段从未被写入，属无效死字段）。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0051_ncfileaccessrule_user_based"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="nc_synced",
        ),
    ]
