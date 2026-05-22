"""Phase 1: NC 集成 — 新建 Position / NcGroup / NcFileAccessRule / NcSyncTask，
重构 UserProfile（移除 roles M2M 和 cloud_id，新增 admin_level / position / extra_nc_groups / nc_synced），
为 Config 新增 config_type 字段，并预置 NC 相关系统参数与内置岗位。
"""
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def seed_builtin_data(apps, schema_editor):
    """预置内置岗位和 NC 配置项。"""
    Position = apps.get_model("api_v1", "Position")
    Config = apps.get_model("api_v1", "Config")

    # 内置岗位
    Position.objects.get_or_create(
        code="sys_admin",
        defaults={
            "name": "系统管理员",
            "is_builtin": True,
            "status": True,
            "order_num": 0,
            "remark": "内置系统管理员岗位，拥有全部菜单权限",
        },
    )
    Position.objects.get_or_create(
        code="member",
        defaults={
            "name": "普通成员",
            "is_builtin": True,
            "status": True,
            "order_num": 99,
            "remark": "内置普通成员岗位，管理员可自定义菜单权限",
        },
    )

    # NC 系统参数预置（均为空值，由管理员在系统配置页填写）
    nc_configs = [
        ("NC_BASE_URL",         "TEXT",     "",                  "Nextcloud 服务地址，如 https://192.168.0.27:40069"),
        ("NC_ADMIN_USER",       "TEXT",     "django_service",    "Nextcloud 服务账号用户名（建议专用账号）"),
        ("NC_ADMIN_APP_PWD",    "PASSWORD", "",                  "Nextcloud 服务账号应用密码（加密存储）"),
        ("NC_DEPT_FOLDER_ROOT", "TEXT",     "/部门文档/",         "部门文档 Group Folder 根路径"),
        ("NC_SHARED_FOLDER",    "TEXT",     "/公司共享/",         "公司共享 Group Folder 路径"),
        ("NC_SHARED_GROUP",     "TEXT",     "company_shared",    "公司共享群组的 NC group_id"),
    ]
    for key, ctype, value, remark in nc_configs:
        Config.objects.get_or_create(
            key=key,
            defaults={
                "value": value,
                "config_type": ctype,
                "remark": remark,
                "status": True,
            },
        )


def set_superuser_admin_level(apps, schema_editor):
    """将 Django 超级用户的 admin_level 设为 COMPANY_ADMIN(1)。"""
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("api_v1", "UserProfile")
    superuser_ids = list(User.objects.filter(is_superuser=True).values_list("id", flat=True))
    if superuser_ids:
        UserProfile.objects.filter(user_id__in=superuser_ids).update(admin_level=1)


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0043_fix_lxorderprofit_pk"),
    ]

    operations = [
        # ── 1. 新建 Position ──────────────────────────────────────────────
        migrations.CreateModel(
            name="Position",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("code", models.CharField(max_length=50, unique=True, verbose_name="岗位编码")),
                ("name", models.CharField(max_length=50, verbose_name="岗位名称")),
                ("status", models.BooleanField(default=True, verbose_name="是否启用")),
                ("is_builtin", models.BooleanField(default=False, help_text="内置岗位不可删除，如 sys_admin、member", verbose_name="是否内置")),
                ("remark", models.CharField(blank=True, default="", max_length=255, verbose_name="备注")),
                ("order_num", models.IntegerField(default=0, verbose_name="排序号")),
                ("menus", models.ManyToManyField(blank=True, related_name="positions", to="api_v1.menu", verbose_name="菜单列表")),
            ],
            options={
                "verbose_name": "岗位",
                "verbose_name_plural": "岗位",
                "ordering": ("order_num", "id"),
            },
        ),

        # ── 2. 新建 NcGroup ───────────────────────────────────────────────
        migrations.CreateModel(
            name="NcGroup",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("code", models.CharField(help_text="Nextcloud 中的 group_id，创建/同步时使用", max_length=100, unique=True, verbose_name="NC 群组 ID")),
                ("name", models.CharField(max_length=100, verbose_name="显示名称")),
                ("group_type", models.CharField(
                    choices=[("DEPT", "部门群组"), ("COMPANY_SHARED", "公司共享群组"), ("CUSTOM", "自定义群组")],
                    default="CUSTOM",
                    max_length=20,
                    verbose_name="群组类型",
                )),
                ("dept", models.OneToOneField(
                    blank=True,
                    help_text="仅 DEPT 类型时绑定对应部门",
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="nc_group",
                    to="api_v1.department",
                    verbose_name="关联部门",
                )),
            ],
            options={
                "verbose_name": "NC 群组",
                "verbose_name_plural": "NC 群组",
                "ordering": ("id",),
            },
        ),

        # ── 3. 新建 NcFileAccessRule ──────────────────────────────────────
        migrations.CreateModel(
            name="NcFileAccessRule",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("nc_path", models.CharField(help_text="如 /部门文档/技术部/", max_length=500, verbose_name="NC 文件夹路径")),
                ("permission_bits", models.IntegerField(default=1, help_text="READ=1 WRITE=2 CREATE=4 DELETE=8 SHARE=16，组合相加", verbose_name="权限位")),
                ("is_group_folder", models.BooleanField(default=True, help_text="True=通过 Group Folders 插件管理；False=OCS 普通共享", verbose_name="是否 Group Folder")),
                ("status", models.BooleanField(default=True, verbose_name="是否生效")),
                ("nc_group", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="file_rules",
                    to="api_v1.ncgroup",
                    verbose_name="NC 群组",
                )),
            ],
            options={
                "verbose_name": "NC 文件访问规则",
                "verbose_name_plural": "NC 文件访问规则",
                "ordering": ("nc_group_id", "nc_path"),
                "unique_together": {("nc_group", "nc_path")},
            },
        ),

        # ── 4. 新建 NcSyncTask ────────────────────────────────────────────
        migrations.CreateModel(
            name="NcSyncTask",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("operation", models.CharField(
                    choices=[
                        ("create_user", "创建 NC 用户"), ("update_user", "更新 NC 用户"),
                        ("disable_user", "禁用 NC 用户"), ("enable_user", "启用 NC 用户"),
                        ("add_to_group", "加入 NC 群组"), ("remove_from_group", "移出 NC 群组"),
                        ("create_group", "创建 NC 群组"), ("set_admin", "设置 NC 管理员"),
                        ("revoke_admin", "撤销 NC 管理员"), ("create_group_folder", "创建 Group Folder"),
                        ("grant_group_folder", "Group Folder 授权群组"),
                    ],
                    max_length=30,
                    verbose_name="操作类型",
                )),
                ("payload", models.JSONField(default=dict, help_text='如 {"username": "zhangsan", "group": "dept_tech"}', verbose_name="操作参数")),
                ("status", models.CharField(
                    choices=[("pending", "待执行"), ("success", "已成功"), ("failed", "已失败")],
                    db_index=True,
                    default="pending",
                    max_length=10,
                    verbose_name="任务状态",
                )),
                ("error_msg", models.TextField(blank=True, default="", verbose_name="错误信息")),
                ("retry_count", models.IntegerField(default=0, verbose_name="已重试次数")),
                ("executed_at", models.DateTimeField(blank=True, null=True, verbose_name="最后执行时间")),
            ],
            options={
                "verbose_name": "NC 同步任务",
                "verbose_name_plural": "NC 同步任务",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="ncsynctask",
            index=models.Index(fields=["status", "retry_count"], name="idx_nc_sync_status_retry"),
        ),

        # ── 5. Config 新增 config_type 字段 ──────────────────────────────
        migrations.AddField(
            model_name="config",
            name="config_type",
            field=models.CharField(
                choices=[("TEXT", "明文"), ("PASSWORD", "加密存储")],
                default="TEXT",
                max_length=10,
                verbose_name="值类型",
            ),
        ),

        # ── 6. UserProfile 新增字段 ───────────────────────────────────────
        migrations.AddField(
            model_name="userprofile",
            name="admin_level",
            field=models.IntegerField(
                choices=[(1, "公司管理员"), (2, "部门管理员"), (3, "普通成员")],
                default=3,
                help_text="COMPANY_ADMIN=全数据+NC管理员；DEPT_ADMIN=本部门数据；MEMBER=仅本人数据",
                verbose_name="管理级别",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="position",
            field=models.ForeignKey(
                blank=True,
                help_text="决定系统菜单权限，由管理员分配",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users",
                to="api_v1.position",
                verbose_name="岗位",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="nc_synced",
            field=models.BooleanField(
                default=False,
                help_text="True=该用户已成功同步到 Nextcloud",
                verbose_name="NC 已同步",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="extra_nc_groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="除部门群组外额外加入的 NC 群组（如项目组、公司共享等）",
                related_name="extra_users",
                to="api_v1.ncgroup",
                verbose_name="额外 NC 群组",
            ),
        ),

        # ── 7. UserProfile 移除旧字段 ─────────────────────────────────────
        migrations.RemoveField(
            model_name="userprofile",
            name="roles",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="cloud_id",
        ),

        # ── 8. 数据迁移：预置内置数据 ────────────────────────────────────
        migrations.RunPython(seed_builtin_data, migrations.RunPython.noop),
        migrations.RunPython(set_superuser_admin_level, migrations.RunPython.noop),
    ]
