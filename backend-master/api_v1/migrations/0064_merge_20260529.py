"""最终合并：将生产端孤立叶节点 0058_merge_20260524_0516 并入主链。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0058_merge_20260524_0516"),
        ("api_v1", "0063_merge_production_leaves"),
    ]

    operations = []
