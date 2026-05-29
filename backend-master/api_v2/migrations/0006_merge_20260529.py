"""合并迁移：将生产端孤立节点 0005_alter_workflowexecution_workflow_type 与本地主链 0005_merge_20260529 收拢。"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0005_alter_workflowexecution_workflow_type"),
        ("api_v2", "0005_merge_20260529"),
    ]

    operations = []
