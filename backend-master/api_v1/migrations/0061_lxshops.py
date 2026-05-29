"""本地占位迁移：与生产端 0061_lxshops 对齐（本地由 0059_create_lx_shops 处理，此处无实际操作）。

生产端存在此迁移文件，本地 lx_shops 表已由 0059_create_lx_shops 创建，此文件仅作占位以保持迁移图一致。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0059_create_lx_shops"),
    ]

    operations = []
