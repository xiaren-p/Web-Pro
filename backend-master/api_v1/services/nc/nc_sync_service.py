"""Nextcloud 用户/群组同步业务逻辑（nc_sync_service）。

负责：
1. 将 Django UserProfile 变更（新建/修改/停用）同步至 Nextcloud。
2. 将 Django Department 变更（新建/修改）同步至 Nextcloud 群组。
3. 对账：查询 NC 已有用户/群组，与本地对比后补齐差异。

调用链：
    view/signal → NcSyncService.xxx() → 写入 NcSyncTask 队列
                                       → 或直接 NcApiClient 调用（快速同步场景）

设计原则：
- 所有 NC 操作先写 NcSyncTask 队列，由 Celery Worker 异步执行；
- NcSyncService 本身仅封装"构造任务 payload"和"直接执行"两种模式；
- 直接执行模式供对账命令（reconcile_nc）使用，不经过队列。
"""
import logging
import secrets
import string

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from api_v1.models.nc.nc_file_access_rule import NcFileAccessRule
from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.models.nc.nc_sync_task import NcSyncTask, SyncOperation, SyncStatus
from api_v1.models.system.user_profile import AdminLevel

logger = logging.getLogger(__name__)
User = get_user_model()

# NC Group Folder 权限位常量（单一来源，供整个服务层引用）
_PERM_READ_ONLY: int = NcFileAccessRule.PERM_READ   # 1 —— 普通成员：仅读
_PERM_FULL: int = NcFileAccessRule.PERM_FULL        # 31 —— 管理员：全权限


class NcSyncService:
    """Nextcloud 同步业务服务类。

    提供两类方法：
    - enqueue_xxx：将任务写入 NcSyncTask 队列（异步执行）。
    - direct_xxx：直接调用 NC API（同步执行，供对账命令使用）。

    Args:
        无（均为静态/类方法，通过 from_settings() 获取 NC 客户端）。
    """

    # ------------------------------------------------------------------ #
    #  入队方法（写 NcSyncTask）                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def enqueue_create_user(username: str, display_name: str, email: str) -> NcSyncTask:
        """入队：在 NC 中创建用户。

        Args:
            username (str): Django 用户名（与 NC username 相同）。
            display_name (str): 显示名称。
            email (str): 邮箱地址。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.CREATE_USER,
            payload={"username": username, "display_name": display_name, "email": email},
        )

    @staticmethod
    def enqueue_update_user(username: str, display_name: str, email: str) -> NcSyncTask:
        """入队：更新 NC 用户信息（显示名称 + 邮箱）。

        Args:
            username (str): Django 用户名。
            display_name (str): 新显示名称。
            email (str): 新邮箱地址。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.UPDATE_USER,
            payload={"username": username, "display_name": display_name, "email": email},
        )

    @staticmethod
    def enqueue_disable_user(username: str) -> NcSyncTask:
        """入队：禁用 NC 用户。

        Args:
            username (str): 目标用户名。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.DISABLE_USER,
            payload={"username": username},
        )

    @staticmethod
    def enqueue_enable_user(username: str) -> NcSyncTask:
        """入队：启用 NC 用户。

        Args:
            username (str): 目标用户名。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.ENABLE_USER,
            payload={"username": username},
        )

    @staticmethod
    def enqueue_set_admin(username: str) -> NcSyncTask:
        """入队：将用户设为 NC 管理员（加入 admin 群组）。

        Args:
            username (str): 目标用户名。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.SET_ADMIN,
            payload={"username": username},
        )

    @staticmethod
    def enqueue_revoke_admin(username: str) -> NcSyncTask:
        """入队：撤销用户 NC 管理员权限（移出 admin 群组）。

        Args:
            username (str): 目标用户名。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.REVOKE_ADMIN,
            payload={"username": username},
        )

    @staticmethod
    def enqueue_add_to_group(username: str, group_code: str) -> NcSyncTask:
        """入队：将用户加入 NC 群组。

        Args:
            username (str): 目标用户名。
            group_code (str): NcGroup.code（即 NC group_id）。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.ADD_TO_GROUP,
            payload={"username": username, "group": group_code},
        )

    @staticmethod
    def enqueue_remove_from_group(username: str, group_code: str) -> NcSyncTask:
        """入队：将用户移出 NC 群组。

        Args:
            username (str): 目标用户名。
            group_code (str): NcGroup.code（即 NC group_id）。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.REMOVE_FROM_GROUP,
            payload={"username": username, "group": group_code},
        )

    @staticmethod
    def enqueue_create_group(group_code: str, display_name: str) -> NcSyncTask:
        """入队：在 NC 中创建群组。

        Args:
            group_code (str): NcGroup.code（即 NC group_id）。
            display_name (str): 群组显示名称。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.CREATE_GROUP,
            payload={"group": group_code, "display_name": display_name},
        )

    @staticmethod
    def enqueue_delete_group(group_code: str) -> NcSyncTask:
        """入队：在 NC 中删除群组。

        Args:
            group_code (str): NcGroup.code（即 NC group_id）。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.DELETE_GROUP,
            payload={"group": group_code},
        )

    @staticmethod
    def enqueue_create_group_folder(group_code: str, mount_point: str) -> NcSyncTask:
        """入队：在 NC 中创建 Group Folder 并将挂载点与群组绑定。

        任务执行后会自动将 NC 返回的 folder_id 回写到 NcGroup，
        并自动入队一条 GRANT_GROUP_FOLDER 任务完成权限授予。

        Args:
            group_code (str): NcGroup.code，用于执行后回写 folder_id。
            mount_point (str): Folder 挂载路径，如 "技术部"。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.CREATE_GROUP_FOLDER,
            payload={"group_code": group_code, "mount_point": mount_point},
        )

    @staticmethod
    def enqueue_grant_group_folder(folder_id: int, group_code: str, permissions: int) -> NcSyncTask:
        """入队：为 Group Folder 授权指定群组。

        Args:
            folder_id (int): NC Group Folder ID。
            group_code (str): NcGroup.code（即 NC group_id）。
            permissions (int): 权限位（普通成员传 _PERM_READ_ONLY=1；管理员传 _PERM_FULL=31）。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.GRANT_GROUP_FOLDER,
            payload={"folder_id": folder_id, "group": group_code, "permissions": permissions},
        )

    @staticmethod
    def enqueue_enable_folder_acl(folder_id: int) -> NcSyncTask:
        """入队：开启 Group Folder 的 ACL 高级权限模式。

        ACL 模式开启后才能对子路径下发细粒度 ACL 规则。幺等，可重复入队。

        Args:
            folder_id (int): NC Group Folder ID。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.ENABLE_FOLDER_ACL,
            payload={"folder_id": folder_id},
        )

    @staticmethod
    def enqueue_set_path_acl(rule: "NcFileAccessRule") -> NcSyncTask:
        """入队：为 Group Folder 内子路径设置用户 ACL 规则。

        将当前规则的所有属性写入 payload，以免后续执行时再次查询 DB。

        Args:
            rule (NcFileAccessRule): 就绪的 NcFileAccessRule 实例（已关联加载 user）。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.SET_PATH_ACL,
            payload={
                "rule_id": rule.id,
                "nc_path": rule.nc_path.strip("/"),
                "username": rule.user.username,
                "permissions": rule.permission_bits,
            },
        )

    @staticmethod
    def enqueue_revoke_path_acl(nc_path: str, username: str) -> NcSyncTask:
        """入队：撤销 Group Folder 内子路径对指定用户的 ACL 规则（mask=0 展透）。

        通过将 acl-mask 设为 0 使该用户的 ACL 条目失效，
        路径权限回退为 Group Folder GRANT 基线。

        Args:
            nc_path (str): 子路径（首尾斜杠将被忽略）。
            username (str): NC 用户名（Django User.username）。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.SET_PATH_ACL,
            payload={
                "rule_id": None,
                "nc_path": nc_path.strip("/"),
                "username": username,
                "permissions": 0,
                "mask": 0,  # mask=0 展透，移除 ACL 限制
            },
        )

    # ------------------------------------------------------------------ #
    #  高级语义方法：用户状态变更入队（供 view 层调用）                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def on_user_created(cls, profile) -> None:
        """用户新建后调用：入队 create_user + 群组同步任务。

        根据 admin_level 决定是否同时入队 set_admin；
        根据 dept 的 NcGroup 入队 add_to_group。

        Args:
            profile: UserProfile 实例（已 save）。
        """
        user = profile.user
        cls.enqueue_create_user(
            username=user.username,
            display_name=profile.nickname or user.username,
            email=user.email or "",
        )
        if profile.admin_level == AdminLevel.COMPANY_ADMIN:
            cls.enqueue_set_admin(user.username)
        cls._enqueue_dept_group(user.username, profile)
        cls._enqueue_dept_admin_group(user.username, profile)  # 仅 DEPT_ADMIN 级别触发
        cls._enqueue_extra_groups(user.username, profile)
        logger.info("[NcSyncService][on_user_created] username=%s 同步任务已入队", user.username)

    @classmethod
    def on_user_updated(
        cls,
        profile,
        old_admin_level: int | None = None,
        old_dept_id: int | None = None,
        old_display_name: str | None = None,
        old_email: str | None = None,
        old_extra_group_codes: set[str] | None = None,
    ) -> None:
        """用户信息更新后调用：入队 update_user、admin 变更、部门群组及额外群组变更任务。

        Args:
            profile: 更新后的 UserProfile 实例。
            old_admin_level (int | None): 变更前的 admin_level（用于判断是否需要升/降 admin）。
            old_dept_id (int | None): 变更前的 dept_id（用于判断是否需要退出旧部门群组）。
            old_display_name (str | None): 变更前的显示名称；为 None 时强制入队 update_user。
            old_email (str | None): 变更前的邮箱；为 None 时强制入队 update_user。
            old_extra_group_codes (set[str] | None): 变更前的额外 NcGroup.code 集合；为 None 时不做差异对比。
        """
        user = profile.user
        new_display_name = profile.nickname or user.username
        new_email = user.email or ""
        # 仅当 display_name 或 email 真实变更时才入队 update_user，避免队列冗余
        if (
            old_display_name is None or old_email is None
            or old_display_name != new_display_name or old_email != new_email
        ):
            cls.enqueue_update_user(
                username=user.username,
                display_name=new_display_name,
                email=new_email,
            )
        if old_admin_level is not None and old_admin_level != profile.admin_level:
            new_level = profile.admin_level
            old_level = old_admin_level

            if new_level == AdminLevel.COMPANY_ADMIN:
                cls.enqueue_set_admin(user.username)
                # 公司管理员通过 NC admin 权限控制，无需活跃在部门管理员群组
                if old_level == AdminLevel.DEPT_ADMIN and profile.dept_id:
                    admin_ng = NcGroup.objects.filter(
                        dept_id=profile.dept_id, group_type=NcGroupType.DEPT_ADMIN,
                    ).first()
                    if admin_ng:
                        cls.enqueue_remove_from_group(user.username, admin_ng.code)
            elif old_level == AdminLevel.COMPANY_ADMIN:
                cls.enqueue_revoke_admin(user.username)
                # 从公司管理员降为部门管理员时，需加入部门管理员群组
                if new_level == AdminLevel.DEPT_ADMIN and profile.dept_id:
                    cls._enqueue_dept_admin_group(user.username, profile)
            elif new_level == AdminLevel.DEPT_ADMIN and old_level == AdminLevel.MEMBER:
                # 普通成员 → 部门管理员：加入部门管理员群组
                cls._enqueue_dept_admin_group(user.username, profile)
            elif new_level == AdminLevel.MEMBER and old_level == AdminLevel.DEPT_ADMIN:
                # 部门管理员 → 普通成员：移出部门管理员群组
                if profile.dept_id:
                    admin_ng = NcGroup.objects.filter(
                        dept_id=profile.dept_id, group_type=NcGroupType.DEPT_ADMIN,
                    ).first()
                    if admin_ng:
                        cls.enqueue_remove_from_group(user.username, admin_ng.code)

        # 部门变更：退出旧部门的 DEPT + DEPT_ADMIN 群组，加入新部门群组
        if old_dept_id != profile.dept_id:
            if old_dept_id:
                for old_ng in NcGroup.objects.filter(
                    dept_id=old_dept_id,
                    group_type__in=[NcGroupType.DEPT, NcGroupType.DEPT_ADMIN],
                ):
                    cls.enqueue_remove_from_group(user.username, old_ng.code)
            cls._enqueue_dept_group(user.username, profile)
            cls._enqueue_dept_admin_group(user.username, profile)
        # 额外群组变更：仅当调用方显式传入 old_extra_group_codes 时对比差集
        if old_extra_group_codes is not None:
            try:
                new_codes = set(profile.extra_nc_groups.values_list("code", flat=True))
            except Exception as exc:
                logger.warning(
                    "[NcSyncService][on_user_updated] username=%s 读取 extra_nc_groups 失败: %s",
                    user.username, exc,
                )
                new_codes = set()
            for code in new_codes - old_extra_group_codes:
                cls.enqueue_add_to_group(user.username, code)
            for code in old_extra_group_codes - new_codes:
                cls.enqueue_remove_from_group(user.username, code)
        logger.info("[NcSyncService][on_user_updated] username=%s 同步任务已入队", user.username)

    @classmethod
    def on_user_status_changed(cls, profile, enabled: bool) -> None:
        """用户启用/停用后调用：入队 enable_user 或 disable_user。

        Args:
            profile: UserProfile 实例。
            enabled (bool): True=启用，False=停用。
        """
        username = profile.user.username
        if enabled:
            cls.enqueue_enable_user(username)
        else:
            cls.enqueue_disable_user(username)
        logger.info("[NcSyncService][on_user_status_changed] username=%s enabled=%s", username, enabled)

    @classmethod
    def on_user_deleted(cls, username: str) -> None:
        """用户在 Django 中删除后调用：入队 disable_user 使其在 NC 侧失效。

        NC 不支持通过 OCS API 直接删除用户（删除会清空数据），
        因此仅禁用账号保留其文件数据，由管理员手动决定是否彻底删除。

        Args:
            username (str): 被删除的 Django 用户名。
        """
        cls.enqueue_disable_user(username)
        logger.info("[NcSyncService][on_user_deleted] username=%s 入队 disable_user", username)

    @classmethod
    def on_dept_created(cls, dept) -> NcGroup:
        """部门新建后调用：同时创建 DEPT + DEPT_ADMIN 双群组并入队同步任务。

        双群组设计：
          DEPT 群组（{code}）           → 普通成员只读（permissions=1）
          DEPT_ADMIN 群组（{code}_admin）→ 管理员全权限（permissions=31）

        Args:
            dept: Department 实例（已 save，id 已赋值）。

        Returns:
            NcGroup: 刚创建的 DEPT 类型 NcGroup 记录。
        """
        base_code = (dept.code or "").strip() or f"dept_{dept.id}"
        admin_code = f"{base_code}_admin"
        with transaction.atomic():
            nc_group, created = NcGroup.objects.get_or_create(
                dept=dept,
                group_type=NcGroupType.DEPT,
                defaults={"code": base_code, "name": dept.name},
            )
            if created:
                admin_nc_group, _ = NcGroup.objects.get_or_create(
                    dept=dept,
                    group_type=NcGroupType.DEPT_ADMIN,
                    defaults={"code": admin_code, "name": f"{dept.name}（管理员）"},
                )
                cls.enqueue_create_group(nc_group.code, nc_group.name)
                cls.enqueue_create_group(admin_nc_group.code, admin_nc_group.name)
                cls.enqueue_create_group_folder(nc_group.code, dept.name)
                logger.info(
                    "[NcSyncService][on_dept_created] dept_id=%s code=%s admin_code=%s "
                    "入队 CREATE_GROUP×2 + CREATE_GROUP_FOLDER",
                    dept.id, nc_group.code, admin_nc_group.code,
                )
            else:
                logger.info(
                    "[NcSyncService][on_dept_created] dept_id=%s NcGroup 已存在，跳过", dept.id,
                )
        return nc_group

    @classmethod
    def on_dept_deleted(cls, dept_id: int) -> None:
        """部门删除前/后调用：入队删除 DEPT + DEPT_ADMIN 群组并清理本地镜像。

        NC 群组删除后成员会挂起无群组，文件夹访问权限随群组删除而失效。

        Args:
            dept_id (int): 被删除部门的 ID。
        """
        nc_groups = list(NcGroup.objects.filter(dept_id=dept_id))
        for nc_group in nc_groups:
            cls.enqueue_delete_group(nc_group.code)
            logger.info(
                "[NcSyncService][on_dept_deleted] dept_id=%s code=%s type=%s 入队 DELETE_GROUP",
                dept_id, nc_group.code, nc_group.group_type,
            )
        NcGroup.objects.filter(id__in=[g.id for g in nc_groups]).delete()

    @classmethod
    def on_dept_updated(cls, dept) -> None:
        """部门名称变更后调用：同步更新 DEPT + DEPT_ADMIN 群组的本地显示名。

        注：NC OCS API 暫不支持直接修改 group displayname，仅更新本地镜像。

        Args:
            dept: 已保存的 Department 实例。
        """
        dept_updated = NcGroup.objects.filter(
            dept=dept, group_type=NcGroupType.DEPT,
        ).update(name=dept.name)
        admin_updated = NcGroup.objects.filter(
            dept=dept, group_type=NcGroupType.DEPT_ADMIN,
        ).update(name=f"{dept.name}（管理员）")
        if dept_updated or admin_updated:
            logger.info(
                "[NcSyncService][on_dept_updated] dept_id=%s name=%s 本地镜像已更新",
                dept.id, dept.name,
            )

    # ------------------------------------------------------------------ #
    #  直接执行方法（供对账命令使用，绕过任务队列）                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def execute_task(task: NcSyncTask) -> bool:
        """直接执行单条 NcSyncTask，更新任务状态。

        Args:
            task (NcSyncTask): 待执行的任务记录。

        Returns:
            bool: 执行成功返回 True，失败返回 False。
        """
        from api_v1.services.nc.nc_api_client import NcApiClient
        try:
            client = NcApiClient.from_settings()
            NcSyncService._dispatch(client, task)
            task.status = SyncStatus.SUCCESS
            task.error_msg = ""
            task.executed_at = timezone.now()
            task.save(update_fields=["status", "error_msg", "executed_at"])
            return True
        except Exception as exc:
            task.retry_count += 1
            task.error_msg = str(exc)[:1000]
            task.executed_at = timezone.now()
            if task.retry_count >= NcSyncTask.MAX_RETRIES:
                task.status = SyncStatus.FAILED
            else:
                # 未超出重试上限，回退为 PENDING 等待下一轮调度
                task.status = SyncStatus.PENDING
            task.save(update_fields=["status", "retry_count", "error_msg", "executed_at"])
            logger.error(
                "[NcSyncService][execute_task] task_id=%s op=%s 执行失败（第%s次）: %s",
                task.id, task.operation, task.retry_count, exc,
                exc_info=True,
            )
            return False

    @staticmethod
    def _dispatch(client, task: NcSyncTask) -> None:
        """根据任务操作类型分发到对应的 NC API 方法。

        Args:
            client (NcApiClient): 已初始化的客户端实例。
            task (NcSyncTask): 待执行的任务记录。

        Raises:
            RuntimeError: 未知操作类型或 NC API 调用失败时抛出。
        """
        op = task.operation
        p = task.payload

        if op == SyncOperation.CREATE_USER:
            # payload 中可追加 password 字段；若无则生成一个符合 NC 密码策略的随机强密码
            if not p.get("password"):
                _chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$"
                nc_password = "".join(secrets.choice(_chars) for _ in range(20))
            else:
                nc_password = p["password"]
            client.create_user(
                username=p["username"],
                password=nc_password,
                display_name=p.get("display_name", ""),
                email=p.get("email", ""),
            )
        elif op == SyncOperation.UPDATE_USER:
            if p.get("display_name"):
                client.update_user_display_name(p["username"], p["display_name"])
            if p.get("email"):
                client.update_user_email(p["username"], p["email"])
        elif op == SyncOperation.DISABLE_USER:
            client.disable_user(p["username"])
        elif op == SyncOperation.ENABLE_USER:
            client.enable_user(p["username"])
        elif op == SyncOperation.SET_ADMIN:
            client.set_admin(p["username"])
        elif op == SyncOperation.REVOKE_ADMIN:
            client.revoke_admin(p["username"])
        elif op == SyncOperation.ADD_TO_GROUP:
            client.add_user_to_group(p["username"], p["group"])
        elif op == SyncOperation.REMOVE_FROM_GROUP:
            client.remove_user_from_group(p["username"], p["group"])
        elif op == SyncOperation.CREATE_GROUP:
            # 幂等：NC 中已存在则跳过，避免 102 冲突反复失败
            if not client.group_exists(p["group"]):
                client.create_group(p["group"], p.get("display_name", ""))
            else:
                logger.info("[NcSyncService][_dispatch] group=%s 已存在，跳过 CREATE_GROUP", p["group"])
        elif op == SyncOperation.DELETE_GROUP:
            # 幂等：群组不存在则视为已删除
            if client.group_exists(p["group"]):
                client.delete_group(p["group"])
            else:
                logger.info("[NcSyncService][_dispatch] group=%s 不存在，跳过 DELETE_GROUP", p["group"])
        elif op == SyncOperation.CREATE_GROUP_FOLDER:
            # 幂等：若本地 NcGroup 已记录 folder_id，说明此前已创建，跳过避免 NC 侧重复 folder
            group_code = p.get("group_code", "")
            existing = NcGroup.objects.filter(code=group_code).first() if group_code else None
            if existing and existing.folder_id:
                logger.info(
                    "[NcSyncService][_dispatch] group=%s folder_id=%s 已存在，跳过 CREATE_GROUP_FOLDER",
                    group_code, existing.folder_id,
                )
            else:
                folder_id = client.create_group_folder(p["mount_point"])
                if group_code:
                    NcGroup.objects.filter(code=group_code).update(folder_id=folder_id)
                    # DEPT 群组：只读（permissions=1）
                    NcSyncService.enqueue_grant_group_folder(
                        folder_id, group_code, permissions=_PERM_READ_ONLY,
                    )
                    # DEPT_ADMIN 群组：全权限（permissions=31）
                    try:
                        nc_group_obj = NcGroup.objects.select_related("dept__parent").get(
                            code=group_code,
                        )
                        if nc_group_obj.dept_id:
                            dept_admin_ng = NcGroup.objects.filter(
                                dept_id=nc_group_obj.dept_id,
                                group_type=NcGroupType.DEPT_ADMIN,
                            ).first()
                            if dept_admin_ng:
                                NcSyncService.enqueue_grant_group_folder(
                                    folder_id, dept_admin_ng.code, permissions=_PERM_FULL,
                                )
                        # 上级部门授权：DEPT 只读，DEPT_ADMIN 全权限
                        parent_dept = nc_group_obj.dept.parent if nc_group_obj.dept else None
                        while parent_dept:
                            parent_dept_ng = NcGroup.objects.filter(
                                dept=parent_dept, group_type=NcGroupType.DEPT,
                            ).first()
                            if parent_dept_ng:
                                NcSyncService.enqueue_grant_group_folder(
                                    folder_id, parent_dept_ng.code, permissions=_PERM_READ_ONLY,
                                )
                            parent_admin_ng = NcGroup.objects.filter(
                                dept=parent_dept, group_type=NcGroupType.DEPT_ADMIN,
                            ).first()
                            if parent_admin_ng:
                                NcSyncService.enqueue_grant_group_folder(
                                    folder_id, parent_admin_ng.code, permissions=_PERM_FULL,
                                )
                            parent_dept = parent_dept.parent
                    except NcGroup.DoesNotExist:
                        pass
                    logger.info(
                        "[NcSyncService][_dispatch] CREATE_GROUP_FOLDER group=%s folder_id=%s 已入队授权",
                        group_code, folder_id,
                    )
        elif op == SyncOperation.GRANT_GROUP_FOLDER:
            client.grant_group_folder(
                folder_id=int(p["folder_id"]),
                group_id=p["group"],
                permissions=int(p["permissions"]),
            )
        elif op == SyncOperation.ENABLE_FOLDER_ACL:
            client.enable_folder_acl(int(p["folder_id"]))
        elif op == SyncOperation.SET_PATH_ACL:
            mask = int(p.get("mask", 31))
            client.set_path_acl(
                nc_path=p["nc_path"],
                username=p["username"],
                mask=mask,
                permissions=int(p["permissions"]),
            )
        else:
            raise RuntimeError(f"[NcSyncService] 未知操作类型: {op}")

    # ------------------------------------------------------------------ #
    #  内部辅助                                                            #
    # ------------------------------------------------------------------ #

    @classmethod
    def _enqueue_dept_group(cls, username: str, profile) -> None:
        """根据用户部门入队 add_to_group（部门 DEPT 群组）。

        Args:
            username (str): 目标用户名。
            profile: UserProfile 实例。
        """
        if not profile.dept_id:
            return
        try:
            nc_group = NcGroup.objects.filter(
                dept_id=profile.dept_id,
                group_type=NcGroupType.DEPT,
            ).first()
            if nc_group:
                cls.enqueue_add_to_group(username, nc_group.code)
        except Exception as exc:
            logger.warning("[NcSyncService][_enqueue_dept_group] username=%s 获取部门群组失败: %s", username, exc)

    @classmethod
    def _enqueue_dept_admin_group(cls, username: str, profile) -> None:
        """仅当用户 admin_level == DEPT_ADMIN 时，入队加入部门管理员 NC 群组。

        COMPANY_ADMIN 通过 NC admin 权限控制，无需加入 DEPT_ADMIN 群组；
        MEMBER 无管理员权限，不加入。

        Args:
            username (str): 目标用户名。
            profile: UserProfile 实例。
        """
        if not profile.dept_id:
            return
        if profile.admin_level != AdminLevel.DEPT_ADMIN:
            return
        try:
            admin_ng = NcGroup.objects.filter(
                dept_id=profile.dept_id,
                group_type=NcGroupType.DEPT_ADMIN,
            ).first()
            if admin_ng:
                cls.enqueue_add_to_group(username, admin_ng.code)
        except Exception as exc:
            logger.warning(
                "[NcSyncService][_enqueue_dept_admin_group] username=%s 获取部门管理员群组失败: %s",
                username, exc,
            )

    @classmethod
    def _enqueue_extra_groups(cls, username: str, profile) -> None:
        """根据用户额外 NC 群组入队 add_to_group。

        Args:
            username (str): 目标用户名。
            profile: UserProfile 实例（需已 save，M2M 可查询）。
        """
        try:
            for nc_group in profile.extra_nc_groups.all():
                cls.enqueue_add_to_group(username, nc_group.code)
        except Exception as exc:
            logger.warning("[NcSyncService][_enqueue_extra_groups] username=%s 获取额外群组失败: %s", username, exc)
