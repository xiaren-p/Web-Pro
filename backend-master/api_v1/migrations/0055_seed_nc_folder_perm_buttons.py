"""在 NC 文件夹权限管理菜单下播种 4 个按钮级权限条目。

该迁移通过 component 字段定位 NC 管理菜单（system/nc/index），
然后创建 4 个 Button 类型子菜单，对应后端 NcFolderTreeViewSet 的 4 组操作：
  - nc:folder:query   → 查询（浏览文件夹树 / 规则列表）
  - nc:folder:mkdir   → 新建文件夹
  - nc:folder:setperm → 设置 ACL 权限规则
  - nc:folder:delete  → 删除权限规则

迁移幂等：若同名 perms 记录已存在则跳过，反向操作不删除（避免生产误删）。
"""
from django.db import migrations


# 待播种的按钮权限列表：(name, perms, order_num)
_NC_BUTTONS = [
    ("查询文件夹", "nc:folder:query", 1),
    ("新建文件夹", "nc:folder:mkdir", 2),
    ("设置权限规则", "nc:folder:setperm", 3),
    ("删除权限规则", "nc:folder:delete", 4),
]

# NC 管理菜单的组件路径（前端 src/views/system/nc/index.vue 对应）
_NC_COMPONENT = "system/nc/index"

# MenuType 枚举值（与 models/system/menu.py 保持一致）
_BUTTON_TYPE = 3


def seed_nc_buttons(apps, schema_editor):
    """创建 NC 文件夹权限管理的按钮级权限菜单条目。"""
    Menu = apps.get_model("api_v1", "Menu")

    # 定位父菜单
    parent = Menu.objects.filter(component=_NC_COMPONENT).first()
    if parent is None:
        # NC 管理菜单尚未在数据库中创建，跳过播种（需先通过菜单管理 UI 创建菜单页）
        return

    existing_perms = set(
        Menu.objects.filter(parent=parent, type=_BUTTON_TYPE)
        .values_list("perms", flat=True)
    )

    to_create = []
    for name, perms, order_num in _NC_BUTTONS:
        if perms in existing_perms:
            continue
        to_create.append(
            Menu(
                name=name,
                parent=parent,
                type=_BUTTON_TYPE,
                perms=perms,
                order_num=order_num,
                visible=False,   # 按钮权限节点不在侧边栏显示
            )
        )

    if to_create:
        Menu.objects.bulk_create(to_create)


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0053_unbuiltin_member_position"),
    ]

    operations = [
        migrations.RunPython(seed_nc_buttons, migrations.RunPython.noop),
    ]
