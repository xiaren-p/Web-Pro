"""合并生产端三个孤立叶节点：0059_merge_20260524_0839 / 0061_lxshops / 0062_lx_ads_profile。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0059_merge_20260524_0839"),
        ("api_v1", "0061_lxshops"),
        ("api_v1", "0062_lx_ads_profile"),
    ]

    operations = []
