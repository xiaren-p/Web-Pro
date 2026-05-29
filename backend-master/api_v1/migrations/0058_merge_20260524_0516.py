"""本地占位迁移：与生产端 0058_merge_20260524_0516 对齐（本地无实际操作）。

生产端存在此合并迁移文件，本地无对应分支，创建空操作占位以保持迁移图一致。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0057_seed_nc_folder_rmdir_button"),
    ]

    operations = []
