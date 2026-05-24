"""在 NC 文件夹权限管理菜单下播种「删除子文件夹」按钮权限条目。

对应后端 NcFolderTreeViewSet 新增的两个 action（folder_delete_preview / delete_folder），
统一收归到同一权限码 nc:folder:rmdir，管理员可按需在岗位权限中开放。

迁移幂等：若同名 perms 记录已存在则跳过，反向操作不删除（避免生产误删）。
"""
from django.db import migrations

# 新增的按钮权限：(name, perms, order_num)
_NEW_BUTTON = ("删除子文件夹", "nc:folder:rmdir", 5)

# NC 管理菜单的组件路径（前端 src/views/system/nc/index.vue 对应）
_NC_COMPONENT = "system/nc/index"

# MenuType 枚举值（与 models/system/menu.py 保持一致）
_BUTTON_TYPE = 3


def seed_rmdir_button(apps, schema_editor):
    """创建 NC 删除子文件夹的按钮级权限菜单条目。"""
    Menu = apps.get_model("api_v1", "Menu")

    # 定位父菜单
    parent = Menu.objects.filter(component=_NC_COMPONENT).first()
    if parent is None:
        # NC 管理菜单尚未创建，跳过播种
        return

    name, perms, order_num = _NEW_BUTTON

    # 幂等检查：已存在则跳过
    if Menu.objects.filter(parent=parent, type=_BUTTON_TYPE, perms=perms).exists():
        return

    Menu.objects.create(
        name=name,
        parent=parent,
        type=_BUTTON_TYPE,
        perms=perms,
        order_num=order_num,
        visible=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0056_position_dept_fk"),
    ]

    operations = [
        migrations.RunPython(seed_rmdir_button, migrations.RunPython.noop),
    ]
