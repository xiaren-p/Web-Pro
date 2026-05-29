"""最终合并：将生产端孤立叶节点 0057_merge_... 与本地主链 0064_merge_20260529 统一收拢。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0057_merge_0056_merge_20260523_1900_0056_position_dept_fk"),
        ("api_v1", "0064_merge_20260529"),
    ]

    operations = []
