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

from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.models.nc.nc_sync_task import NcSyncTask, SyncOperation, SyncStatus
from api_v1.models.system.user_profile import AdminLevel

logger = logging.getLogger(__name__)
User = get_user_model()


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
    def enqueue_grant_group_folder(folder_id: int, group_code: str, permissions: int = 31) -> NcSyncTask:
        """入队：为 Group Folder 授权指定群组。

        Args:
            folder_id (int): NC Group Folder ID。
            group_code (str): NcGroup.code（即 NC group_id）。
            permissions (int): 权限位（READ=1 WRITE=2 CREATE=4 DELETE=8 SHARE=16，默认 31=全部）。

        Returns:
            NcSyncTask: 已创建的任务记录。
        """
        return NcSyncTask.objects.create(
            operation=SyncOperation.GRANT_GROUP_FOLDER,
            payload={"folder_id": folder_id, "group": group_code, "permissions": permissions},
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
        cls._enqueue_extra_groups(user.username, profile)
        logger.info("[NcSyncService][on_user_created] username=%s 同步任务已入队", user.username)

    @classmethod
    def on_user_updated(cls, profile, old_admin_level: int | None = None, old_dept_id: int | None = None) -> None:
        """用户信息更新后调用：入队 update_user、admin 变更及部门群组变更任务。

        Args:
            profile: 更新后的 UserProfile 实例。
            old_admin_level (int | None): 变更前的 admin_level（用于判断是否需要升/降 admin）。
            old_dept_id (int | None): 变更前的 dept_id（用于判断是否需要退出旧部门群组）。
        """
        user = profile.user
        cls.enqueue_update_user(
            username=user.username,
            display_name=profile.nickname or user.username,
            email=user.email or "",
        )
        if old_admin_level is not None and old_admin_level != profile.admin_level:
            if profile.admin_level == AdminLevel.COMPANY_ADMIN:
                cls.enqueue_set_admin(user.username)
            elif old_admin_level == AdminLevel.COMPANY_ADMIN:
                cls.enqueue_revoke_admin(user.username)
        # 部门变更：退出旧部门群组，加入新部门群组
        # 注意：old_dept_id 可能为 None（用户原本无部门），此时条件仅判断是否与新値不同
        if old_dept_id != profile.dept_id:
            if old_dept_id:
                old_nc_group = NcGroup.objects.filter(
                    dept_id=old_dept_id, group_type=NcGroupType.DEPT,
                ).first()
                if old_nc_group:
                    cls.enqueue_remove_from_group(user.username, old_nc_group.code)
            cls._enqueue_dept_group(user.username, profile)
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
        """部门新建后调用：自动创建 NcGroup 镜像并入队 CREATE_GROUP 任务。

        NC group_id（即 NcGroup.code）优先取 dept.code，若为空则回退为 dept_{dept.id}。
        该方法在同一事务内完成 NcGroup 写入，CREATE_GROUP 任务入队后由 Celery 异步执行。

        Args:
            dept: Department 实例（已 save，id 已赋值）。

        Returns:
            NcGroup: 刚创建的 NcGroup 记录。
        """
        code = (dept.code or "").strip() or f"dept_{dept.id}"
        with transaction.atomic():
            nc_group, created = NcGroup.objects.get_or_create(
                dept=dept,
                defaults={
                    "code": code,
                    "name": dept.name,
                    "group_type": NcGroupType.DEPT,
                },
            )
            if created:
                cls.enqueue_create_group(nc_group.code, nc_group.name)
                cls.enqueue_create_group_folder(nc_group.code, dept.name)
                logger.info(
                    "[NcSyncService][on_dept_created] dept_id=%s code=%s 入队 CREATE_GROUP + CREATE_GROUP_FOLDER",
                    dept.id, nc_group.code,
                )
            else:
                logger.info(
                    "[NcSyncService][on_dept_created] dept_id=%s NcGroup 已存在，跳过", dept.id,
                )
        return nc_group

    @classmethod
    def on_dept_updated(cls, dept) -> None:
        """部门名称变更后调用：同步更新 NcGroup 的显示名称（本地镜像）。

        注：NC OCS API 暂不支持直接修改 group displayname，仅更新本地镜像记录。

        Args:
            dept: 已保存的 Department 实例。
        """
        updated = NcGroup.objects.filter(dept=dept, group_type=NcGroupType.DEPT).update(
            name=dept.name,
        )
        if updated:
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
            client.create_group(p["group"], p.get("display_name", ""))
        elif op == SyncOperation.CREATE_GROUP_FOLDER:
            folder_id = client.create_group_folder(p["mount_point"])
            # 回写 folder_id 到 NcGroup，并自动入队授权任务
            group_code = p.get("group_code", "")
            if group_code:
                NcGroup.objects.filter(code=group_code).update(folder_id=folder_id)
                NcSyncService.enqueue_grant_group_folder(folder_id, group_code)
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
        else:
            raise RuntimeError(f"[NcSyncService] 未知操作类型: {op}")

    # ------------------------------------------------------------------ #
    #  内部辅助                                                            #
    # ------------------------------------------------------------------ #

    @classmethod
    def _enqueue_dept_group(cls, username: str, profile) -> None:
        """根据用户部门入队 add_to_group（部门对应的 NcGroup）。

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
