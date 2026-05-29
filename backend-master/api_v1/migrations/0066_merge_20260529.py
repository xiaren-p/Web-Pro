"""最终合并：将生产端孤立叶节点 0054_alter_position_is_builtin 与本地主链 0065_merge_20260529 统一收拢。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0054_alter_position_is_builtin"),
        ("api_v1", "0065_merge_20260529"),
    ]

    operations = []
