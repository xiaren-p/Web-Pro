"""占位迁移：对齐生产端 0003_alter_workflowexecution_workflow_type（本地从未生成此节点）。"""

from django.db import migrations


class Migration(migrations.Migration):
    """生产端直接执行 makemigrations 产生的孤立节点，本地以占位补齐。"""

    dependencies = [
        ("api_v2", "0002_aduploadqueue"),
    ]

    operations = []
