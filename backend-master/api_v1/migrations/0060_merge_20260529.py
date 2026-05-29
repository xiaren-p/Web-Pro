"""Merge 迁移：合并 0059_create_lx_shops 与 0059_merge_20260524_0839 两条分叉叶节点。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0059_create_lx_shops"),
        ("api_v1", "0059_merge_20260524_0839"),
    ]

    operations = []
