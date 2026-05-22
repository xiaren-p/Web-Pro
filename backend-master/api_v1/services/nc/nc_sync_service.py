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

from django.contrib.auth import get_user_model
from django.db import transaction

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
    def on_user_updated(cls, profile, old_admin_level: int | None = None) -> None:
        """用户信息更新后调用：入队 update_user 及可能的 admin 变更任务。

        Args:
            profile: 更新后的 UserProfile 实例。
            old_admin_level (int | None): 变更前的 admin_level（用于判断是否需要升/降 admin）。
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
            task.save(update_fields=["status", "error_msg", "updated_time"])
            return True
        except Exception as exc:
            task.retry_count += 1
            task.error_msg = str(exc)[:1000]
            if task.retry_count >= NcSyncTask.MAX_RETRIES:
                task.status = SyncStatus.FAILED
            task.save(update_fields=["status", "retry_count", "error_msg", "updated_time"])
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
            client.create_user(
                username=p["username"],
                password=p.get("password", "TmpPass@2024!"),
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
            client.create_group_folder(p["mount_point"])
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
