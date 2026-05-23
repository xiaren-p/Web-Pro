"""将 member 岗位的 is_builtin 改为 False，仅保留 sys_admin 为内置岗位。"""
from django.db import migrations


def unbuiltin_member(apps, schema_editor):
    """取消 member 岗位的内置保护。"""
    Position = apps.get_model("api_v1", "Position")
    Position.objects.filter(code="member", is_builtin=True).update(is_builtin=False)


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0052_remove_userprofile_nc_synced"),
    ]

    operations = [
        migrations.RunPython(unbuiltin_member, migrations.RunPython.noop),
    ]
