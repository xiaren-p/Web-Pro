"""reconcile_nc：Nextcloud 全量对账管理命令。

对比本地 UserProfile 与 NC 实际状态，补齐缺失的用户/群组成员关系。
适用场景：首次迁移、NC 故障恢复后、人工排查不一致时使用。

用法：
    python manage.py reconcile_nc [--dry-run] [--user <username>]
"""
import logging
import os
import tempfile
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from api_v1.models import Department
from api_v1.models.nc.nc_file_access_rule import NcFileAccessRule
from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.models.nc.nc_sync_task import NcSyncTask, SyncOperation, SyncStatus
from api_v1.models.system.user_profile import AdminLevel, UserProfile
from api_v1.services.nc.nc_api_client import NcApiClient
from api_v1.services.nc.nc_sync_service import NcSyncService

logger = logging.getLogger(__name__)
User = get_user_model()

# NC Group Folder 权限位常量（与 nc_sync_service.py 中保持一致）
_PERM_READ_ONLY: int = NcFileAccessRule.PERM_READ  # 1 —— 普通成员只读
_PERM_FULL: int = NcFileAccessRule.PERM_FULL       # 31 —— 管理员全权限


class Command(BaseCommand):
    """Nextcloud 全量对账命令：对比本地用户与 NC 现有用户，补齐差异。

    对账规则：
    1. 本地 is_active=True 的用户在 NC 不存在 → 创建 NC 用户。
    2. 本地 admin_level=COMPANY_ADMIN 的用户在 NC 不在 admin 群组 → 入队 set_admin。
    3. 本地 is_active=False 的用户在 NC 处于启用态 → 入队 disable_user。
    4. 失败的 NcSyncTask（retry_count < MAX_RETRIES）→ 重置为 PENDING 重试。
    """

    help = "对账本地用户与 Nextcloud 用户状态，补齐缺失的同步任务。"

    def add_arguments(self, parser) -> None:
        """注册命令行参数。

        Args:
            parser: argparse.ArgumentParser 实例。
        """
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="仅打印需要同步的操作，不实际写入 NcSyncTask 或调用 NC API。",
        )
        parser.add_argument(
            "--user",
            dest="username",
            default=None,
            help="仅对账指定用户名（不传则对账全部活跃用户）。",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            default=False,
            help="对账完成后立即直接执行所有 PENDING 任务（不等待 Celery Worker）。",
        )

    def handle(self, *args, **options) -> None:
        """命令入口：执行对账逻辑（带文件锁防止并发）。

        Args:
            *args: 不使用。
            **options (dict): 命令行选项字典，包含 dry_run / username / execute。

        Raises:
            CommandError: NC API 初始化失败或已有实例正在运行时抛出。
        """
        # 并发锁：避免多个 reconcile_nc 同时跑导致任务重复入队 / 抢任务
        lock_path = os.path.join(tempfile.gettempdir(), "reconcile_nc.lock")
        if os.path.exists(lock_path):
            try:
                with open(lock_path, "r", encoding="utf-8") as f:
                    old_pid = int((f.read() or "0").strip() or "0")
                if old_pid > 0:
                    try:
                        os.kill(old_pid, 0)  # 仅探测进程存活
                        raise CommandError(
                            f"另一个 reconcile_nc 进程正在运行 (pid={old_pid})，请等待其完成后重试。"
                        )
                    except ProcessLookupError:
                        pass  # 旧进程已退出，可覆写锁
            except (ValueError, OSError):
                pass
        try:
            with open(lock_path, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            self._run(options)
        finally:
            try:
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except OSError:
                pass

    def _run(self, options: dict) -> None:
        """对账主流程（在并发锁保护下运行）。

        Args:
            options (dict): 命令行选项。

        Raises:
            CommandError: NC API 初始化失败时抛出。
        """
        dry_run: bool = options["dry_run"]
        target_username: str | None = options["username"]
        execute: bool = options["execute"]

        # 初始化 NC 客户端（对账需要查询 NC 状态）
        try:
            client = NcApiClient.from_settings()
        except RuntimeError as exc:
            raise CommandError(f"无法连接 Nextcloud，请检查 Config 配置: {exc}") from exc

        self.stdout.write(self.style.NOTICE(
            f"[reconcile_nc] 开始对账 | dry_run={dry_run} | target={target_username or '全部'}"
        ))

        # 获取需要对账的用户列表
        qs = UserProfile.objects.select_related("user", "dept").prefetch_related("extra_nc_groups")
        if target_username:
            qs = qs.filter(user__username=target_username)
        profiles = list(qs)

        enqueued = 0
        skipped = 0

        # ------------------------------------------------------------ #
        # Step 0: 为没有 NcGroup 镜像记录的部门补建本地记录
        # 适用场景：部门在 NC 同步功能上线前就已存在，on_dept_created 未被调用
        # ------------------------------------------------------------ #
        if not target_username:
            # 查找尚无 DEPT 群组的部门
            depts_without_group = Department.objects.exclude(
                nc_groups__group_type=NcGroupType.DEPT
            )
            for dept in depts_without_group:
                base_code = (dept.code or "").strip() or f"dept_{dept.id}"
                admin_code = f"{base_code}_admin"
                # 唯一性兜底：若 code 冲突，回退至 dept_{id}，仍冲突则附时间戳
                code = base_code
                if NcGroup.objects.filter(code=code).exclude(dept=dept).exists():
                    fallback = f"dept_{dept.id}"
                    if not NcGroup.objects.filter(code=fallback).exists():
                        code = fallback
                    else:
                        code = f"dept_{dept.id}_{int(time.time())}"
                admin_code_resolved = admin_code
                if NcGroup.objects.filter(code=admin_code_resolved).exclude(dept=dept).exists():
                    admin_code_resolved = f"dept_{dept.id}_admin_{int(time.time())}"
                try:
                    nc_group = NcGroup.objects.create(
                        dept=dept,
                        code=code,
                        name=dept.name,
                        group_type=NcGroupType.DEPT,
                    )
                    NcGroup.objects.get_or_create(
                        dept=dept,
                        group_type=NcGroupType.DEPT_ADMIN,
                        defaults={
                            "code": admin_code_resolved,
                            "name": f"{dept.name}（管理员）",
                        },
                    )
                except IntegrityError as exc:
                    logger.warning(
                        "[reconcile_nc] 补建 NcGroup 失败 dept_id=%s code=%s err=%s",
                        dept.id, code, exc,
                    )
                    skipped += 1
                    continue
                self.stdout.write(
                    f"  → 补建 NcGroup: [{dept.name}] DEPT={nc_group.code} ADMIN={admin_code_resolved}"
                )
                logger.info(
                    "[reconcile_nc] 补建 NcGroup dept_id=%s code=%s admin_code=%s",
                    dept.id, code, admin_code_resolved,
                )
                # 立即入队 NC 群组与 Group Folder 创建，避免依赖 Step 1 才发现
                if not dry_run:
                    NcSyncService.enqueue_create_group(nc_group.code, nc_group.name)
                    admin_ng = NcGroup.objects.filter(
                        dept=dept, group_type=NcGroupType.DEPT_ADMIN
                    ).first()
                    if admin_ng:
                        NcSyncService.enqueue_create_group(admin_ng.code, admin_ng.name)
                    NcSyncService.enqueue_create_group_folder(nc_group.code, dept.name)
                    enqueued += 3

        # ------------------------------------------------------------ #
        # Step 1: 对账 NC 群组是否存在（本地 NcGroup 记录 vs NC 实际状态）
        # ------------------------------------------------------------ #
        if not target_username:
            for nc_group in NcGroup.objects.all():
                try:
                    nc_group_exists = client.group_exists(nc_group.code)
                except Exception as exc:
                    logger.warning("[reconcile_nc] 查询 NC 群组 %s 失败，跳过: %s", nc_group.code, exc)
                    continue
                if not nc_group_exists:
                    self.stdout.write(f"  → NC 群组不存在，需创建: {nc_group.code} ({nc_group.get_group_type_display()})")
                    if not dry_run:
                        NcSyncService.enqueue_create_group(nc_group.code, nc_group.name)
                        enqueued += 1

        # ------------------------------------------------------------ #
        # Step 2: 逐用户对账
        # ------------------------------------------------------------ #
        for profile in profiles:
            username = profile.user.username
            is_active = profile.user.is_active
            try:
                nc_exists = client.user_exists(username)
            except Exception as exc:
                logger.warning("[reconcile_nc] 查询 NC 用户 %s 失败，跳过: %s", username, exc)
                skipped += 1
                continue

            if is_active and not nc_exists:
                # 需要创建
                self.stdout.write(f"  → 需创建 NC 用户: {username}")
                if not dry_run:
                    NcSyncService.enqueue_create_user(
                        username=username,
                        display_name=profile.nickname or username,
                        email=profile.user.email or "",
                    )
                    # 入队 admin 权限
                    if profile.admin_level == AdminLevel.COMPANY_ADMIN:
                        NcSyncService.enqueue_set_admin(username)
                    # 入队部门群组
                    NcSyncService._enqueue_dept_group(username, profile)
                    NcSyncService._enqueue_dept_admin_group(username, profile)
                    NcSyncService._enqueue_extra_groups(username, profile)
                    enqueued += 1

            elif is_active and nc_exists:
                # 用户已在 NC 中：对账启用状态与群组成员关系
                try:
                    nc_user_data = client.get_user(username)
                    nc_enabled: bool = nc_user_data.get("enabled", True)
                    nc_groups: set = set(nc_user_data.get("groups", []))
                except Exception as exc:
                    logger.warning("[reconcile_nc] 获取 NC 用户 %s 详情失败，跳过: %s", username, exc)
                    skipped += 1
                    continue

                # 对账启用状态
                if not nc_enabled:
                    self.stdout.write(f"  → NC 用户已被禁用但本地活跃，需重新启用: {username}")
                    if not dry_run:
                        NcSyncService.enqueue_enable_user(username)
                        enqueued += 1

                # 对账群组成员关系
                expected_groups: set = set()
                if profile.dept_id:
                    dept_nc_group = NcGroup.objects.filter(
                        dept_id=profile.dept_id,
                        group_type=NcGroupType.DEPT,
                    ).first()
                    if dept_nc_group:
                        expected_groups.add(dept_nc_group.code)
                    # DEPT_ADMIN 级别的用户需同时在部门管理员群组
                    if profile.admin_level == AdminLevel.DEPT_ADMIN:
                        admin_nc_group = NcGroup.objects.filter(
                            dept_id=profile.dept_id,
                            group_type=NcGroupType.DEPT_ADMIN,
                        ).first()
                        if admin_nc_group:
                            expected_groups.add(admin_nc_group.code)
                for extra_g in profile.extra_nc_groups.all():
                    expected_groups.add(extra_g.code)
                if profile.admin_level == AdminLevel.COMPANY_ADMIN:
                    expected_groups.add("admin")

                for missing_group in expected_groups - nc_groups:
                    self.stdout.write(f"  → 用户 {username} 未在群组 {missing_group}，需加入")
                    if not dry_run:
                        NcSyncService.enqueue_add_to_group(username, missing_group)
                        enqueued += 1

                # 反向差集：NC 中存在但本地不再期望的群组（admin 由 admin_level 单独管控，跳过）
                # 仅清理本地 NcGroup 知道的群组，避免误删 NC 中其它系统群组
                known_codes: set = set(NcGroup.objects.values_list("code", flat=True))
                extra_groups = (nc_groups - expected_groups) & known_codes
                extra_groups.discard("admin")
                for stale_group in extra_groups:
                    self.stdout.write(f"  → 用户 {username} 多余群组 {stale_group}，需移除")
                    if not dry_run:
                        NcSyncService.enqueue_remove_from_group(username, stale_group)
                        enqueued += 1

            elif not is_active and nc_exists:
                # 需要禁用
                self.stdout.write(f"  → 需禁用 NC 用户: {username}")
                if not dry_run:
                    NcSyncService.enqueue_disable_user(username)
                    enqueued += 1

        # 反向扫描：从 NC 已有的 Group Folder 中认领系统已知部门群组
        # 场景：管理员在 NC 端手动将部门群组加入某 Group Folder，
        # 此时 DB 里的 NcGroup.folder_id 仍为 NULL，reconcile 会误判为"需新建"。
        # 本步先扫描 NC folder 成员列表，将 folder_id 回写到 DB，
        # 避免后续步骤重复创建同名 Group Folder。
        if not target_username:
            try:
                _nc_folders_for_import = client.list_group_folders()
            except RuntimeError as exc:
                logger.warning("[reconcile_nc] 无法获取 NC Group Folder 列表，跳过反向扫描: %s", exc)
                _nc_folders_for_import = {}

            if _nc_folders_for_import:
                # 构建 group_code → folder_id 反向映射（取 NC 数据中第一次出现的对应关系）
                _code_to_folder: dict[str, int] = {}
                for _fid, _finfo in _nc_folders_for_import.items():
                    for _gc in (_finfo.get("groups") or {}):
                        if _gc not in _code_to_folder:
                            _code_to_folder[_gc] = _fid

                # 仅对 folder_id 为空的 DEPT 群组做回写
                _dept_no_folder = NcGroup.objects.filter(
                    group_type=NcGroupType.DEPT,
                    folder_id__isnull=True,
                    dept__isnull=False,
                )
                for _ng in _dept_no_folder:
                    _discovered_fid = _code_to_folder.get(_ng.code)
                    if _discovered_fid is not None:
                        self.stdout.write(
                            f"  → 反向发现 Group Folder：群组 {_ng.code} "
                            f"已在 NC folder_id={_discovered_fid} 中，回写 DB"
                        )
                        logger.info(
                            "[reconcile_nc] 反向发现 folder_id：group=%s folder_id=%s",
                            _ng.code, _discovered_fid,
                        )
                        if not dry_run:
                            _ng.folder_id = _discovered_fid
                            _ng.save(update_fields=["folder_id"])

        # 对账部门 Group Folder：有 NcGroup 但 folder_id 为空的部门
        # （经上方反向扫描后，已认领的部门群组不会再触发此分支）
        if not target_username:
            dept_missing_folder = NcGroup.objects.filter(
                group_type=NcGroupType.DEPT,
                folder_id__isnull=True,
                dept__isnull=False,
            ).select_related("dept")
            for nc_group in dept_missing_folder:
                self.stdout.write(f"  → 部门群组缺少 Group Folder: {nc_group.code}")
                if not dry_run:
                    NcSyncService.enqueue_create_group_folder(nc_group.code, nc_group.dept.name)
                    enqueued += 1

        # 对账部门 Group Folder：folder_id 有值但 NC 中已被删除（如管理员手动误删）
        # 注意：CREATE_GROUP_FOLDER 任务有幂等保护（folder_id 非空时跳过），
        # 必须先清空本地 folder_id 再入队，否则任务会静默跳过。
        if not target_username:
            try:
                _nc_folders_existing = client.list_group_folders()
                _existing_folder_ids: set[int] = set(_nc_folders_existing.keys())
            except RuntimeError as exc:
                logger.warning("[reconcile_nc] 无法获取 NC Group Folder 列表，跳过 folder 删除检测: %s", exc)
                _existing_folder_ids = set()

            if _existing_folder_ids is not None:
                dept_deleted_folder = (
                    NcGroup.objects.filter(
                        group_type=NcGroupType.DEPT,
                        folder_id__isnull=False,
                        dept__isnull=False,
                    )
                    .exclude(folder_id__in=_existing_folder_ids)
                    .select_related("dept")
                )
                for nc_group in dept_deleted_folder:
                    self.stdout.write(
                        f"  → Group Folder 已从 NC 删除，将重建: {nc_group.code}"
                        f" (旧 folder_id={nc_group.folder_id})"
                    )
                    logger.warning(
                        "[reconcile_nc] Group Folder 已被删除 group=%s folder_id=%s，清空并重建",
                        nc_group.code, nc_group.folder_id,
                    )
                    if not dry_run:
                        # 必须先清空 folder_id，CREATE_GROUP_FOLDER 任务才不会被幂等保护跳过
                        nc_group.folder_id = None
                        nc_group.save(update_fields=["folder_id"])
                        NcSyncService.enqueue_create_group_folder(nc_group.code, nc_group.dept.name)
                        enqueued += 1

        # 对账上级部门对下级文件夹的授权
        # DEPT 群组的上级授权应为只读（permissions=1）。
        # DEPT_ADMIN 群组的上级授权应为全权限（permissions=31）。
        # 对存量权限不符（如旧的 31）的直接重新授权覆盖（备忘: 用户确认直接降权）。
        if not target_username:
            dept_groups_with_folder = NcGroup.objects.filter(
                group_type=NcGroupType.DEPT,
                folder_id__isnull=False,
                dept__isnull=False,
            ).select_related("dept__parent")
            if dept_groups_with_folder.exists():
                try:
                    nc_folders = client.list_group_folders()
                except RuntimeError as exc:
                    logger.warning("[reconcile_nc] 无法获取 NC 文件夹列表，跳过上级授权对账: %s", exc)
                    nc_folders = {}
                for nc_group in dept_groups_with_folder:
                    folder_info = nc_folders.get(nc_group.folder_id)
                    if not folder_info:
                        continue
                    folder_groups: dict = folder_info.get("groups", {})

                    # 检查自身 DEPT 群组权限是否正确（存量降权）
                    # NC groups 字段格式为 {group_code: permissions_int}，直接取整数值
                    own_perms = folder_groups.get(nc_group.code, -1)
                    if nc_group.code in folder_groups and own_perms != _PERM_READ_ONLY:
                        self.stdout.write(
                            f"  → DEPT 群组权限不符，重新授权: {nc_group.code} "
                            f"当前={own_perms} 应为={_PERM_READ_ONLY}"
                        )
                        if not dry_run:
                            NcSyncService.enqueue_grant_group_folder(
                                nc_group.folder_id, nc_group.code, permissions=_PERM_READ_ONLY,
                            )
                            enqueued += 1

                    # 检查 DEPT_ADMIN 群组权限
                    dept_admin_ng = NcGroup.objects.filter(
                        dept_id=nc_group.dept_id, group_type=NcGroupType.DEPT_ADMIN,
                    ).first()
                    if dept_admin_ng:
                        admin_perms = folder_groups.get(dept_admin_ng.code, -1)
                        if admin_perms != _PERM_FULL:
                            self.stdout.write(
                                f"  → DEPT_ADMIN 群组权限不符，重新授权: {dept_admin_ng.code} "
                                f"当前={admin_perms} 应为={_PERM_FULL}"
                            )
                            if not dry_run:
                                NcSyncService.enqueue_grant_group_folder(
                                    nc_group.folder_id, dept_admin_ng.code, permissions=_PERM_FULL,
                                )
                                enqueued += 1

                    # 上级部门授权对账
                    parent_dept = nc_group.dept.parent
                    while parent_dept:
                        parent_dept_ng = NcGroup.objects.filter(
                            dept=parent_dept, group_type=NcGroupType.DEPT,
                        ).first()
                        if parent_dept_ng:
                            p_perms = folder_groups.get(parent_dept_ng.code, -1)
                            if p_perms != _PERM_READ_ONLY:
                                self.stdout.write(
                                    f"  → 上级 DEPT 授权不符: folder_id={nc_group.folder_id} "
                                    f"{nc_group.code} ← ancestor={parent_dept_ng.code}"
                                )
                                if not dry_run:
                                    NcSyncService.enqueue_grant_group_folder(
                                        nc_group.folder_id,
                                        parent_dept_ng.code,
                                        permissions=_PERM_READ_ONLY,
                                    )
                                    enqueued += 1
                        parent_admin_ng = NcGroup.objects.filter(
                            dept=parent_dept, group_type=NcGroupType.DEPT_ADMIN,
                        ).first()
                        if parent_admin_ng:
                            pa_perms = folder_groups.get(parent_admin_ng.code, -1)
                            if pa_perms != _PERM_FULL:
                                self.stdout.write(
                                    f"  → 上级 DEPT_ADMIN 授权不符: folder_id={nc_group.folder_id} "
                                    f"← ancestor_admin={parent_admin_ng.code}"
                                )
                                if not dry_run:
                                    NcSyncService.enqueue_grant_group_folder(
                                        nc_group.folder_id,
                                        parent_admin_ng.code,
                                        permissions=_PERM_FULL,
                                    )
                                    enqueued += 1
                        parent_dept = parent_dept.parent

        # ------------------------------------------------------------ #
        # Step 5: 对账 NcFileAccessRule 子目录 ACL 规则
        # 遇到生效规则（status=True）→ 确保对应文件夹已开 ACL 模式 → 入队 SET_PATH_ACL
        # NcFileAccessRule 无 nc_group 字段，通过 nc_path 首段得到 mount_point，
        # 再经 NC API list_group_folders() 定位 folder_id（避免 dept.name 重命名失配）。
        # ------------------------------------------------------------ #
        if not target_username:
            # 预取 NC 所有 Group Folder：mount_point（去除首尾斜杠）→ folder_id
            try:
                _nc_folders = client.list_group_folders()
                nc_mount_to_folder_id: dict[str, int] = {
                    info.get("mount_point", "").strip("/"): fid
                    for fid, info in _nc_folders.items()
                }
            except RuntimeError:
                logger.warning("[reconcile_nc] 无法获取 NC Group Folder 列表，跳过 Step 5 ACL 对账")
                nc_mount_to_folder_id = {}

            active_rules = NcFileAccessRule.objects.filter(
                status=True,
            ).select_related("user")
            acl_enqueued = 0
            for rule in active_rules:
                # nc_path 格式：<mount_point>[/<子路径>]，首尾无斜杠
                mount_point = rule.nc_path.split("/")[0]
                folder_id_for_acl: int | None = nc_mount_to_folder_id.get(mount_point)
                if not folder_id_for_acl:
                    logger.warning(
                        "[reconcile_nc] ACL 规则 rule_id=%s mount_point=%s 无法定位 folder_id，跳过",
                        rule.id, mount_point,
                    )
                    continue
                # 通过 folder_id 找到对应的 DEPT 群组（用于 add_to_group）
                dept_ng_for_rule = NcGroup.objects.filter(
                    group_type=NcGroupType.DEPT,
                    folder_id=folder_id_for_acl,
                ).first()
                self.stdout.write(
                    f"  → ACL 规则对账: [{mount_point}] {rule.nc_path}"
                    f" user={rule.user.username} perms={rule.permission_bits}"
                )
                if not dry_run:
                    NcSyncService.enqueue_enable_folder_acl(folder_id_for_acl)
                    if dept_ng_for_rule:
                        NcSyncService.enqueue_add_to_group(
                            rule.user.username, dept_ng_for_rule.code
                        )
                    NcSyncService.enqueue_set_path_acl(rule)
                    acl_enqueued += 1
            if acl_enqueued:
                self.stdout.write(f"  → ACL 规则入队共 {acl_enqueued} 条（每条包含 ENABLE_FOLDER_ACL + SET_PATH_ACL）")
                enqueued += acl_enqueued * 2

        # 重置失败任务
        failed_qs = NcSyncTask.objects.filter(
            status=SyncStatus.FAILED,
            retry_count__lt=NcSyncTask.MAX_RETRIES,
        )
        failed_count = failed_qs.count()
        if failed_count:
            self.stdout.write(f"  → 重置 {failed_count} 条 FAILED 任务为 PENDING")
            if not dry_run:
                failed_qs.update(status=SyncStatus.PENDING)

        self.stdout.write(self.style.SUCCESS(
            f"[reconcile_nc] 对账完成 | enqueued={enqueued} skipped={skipped} failed_reset={failed_count if not dry_run else 0}"
        ))

        if execute and not dry_run:
            self._execute_pending()

    def _execute_pending(self) -> None:
        """立即执行所有 PENDING 任务（不经 Celery，适合一次性对账场景）。

        说明：
        - 每条任务间插入 0.5s 间隔，避免短时间内对 NC 发起过密请求触发限流或锁竞争。
        - 采用循环快照策略：每轮从 DB 重新拉取 PENDING 列表，直到没有新任务为止。
          这样执行过程中入队的子任务（如 CREATE_GROUP_FOLDER 派生的 GRANT_GROUP_FOLDER）
          会在下一轮被自动拾起，无需依赖 Celery 或手动二次执行。
        """
        success = 0
        failed = 0
        round_num = 0
        while True:
            round_num += 1
            pending = list(NcSyncTask.objects.filter(status=SyncStatus.PENDING).order_by("id"))
            if not pending:
                break
            self.stdout.write(self.style.NOTICE(
                f"[reconcile_nc] 第 {round_num} 轮：执行 {len(pending)} 条 PENDING 任务..."
            ))
            for idx, task in enumerate(pending):
                ok = NcSyncService.execute_task(task)
                if ok:
                    success += 1
                else:
                    failed += 1
                # 限流：最后一条不再 sleep
                if idx < len(pending) - 1:
                    time.sleep(0.5)
        self.stdout.write(self.style.SUCCESS(
            f"[reconcile_nc] 执行完毕 | success={success} failed={failed}"
        ))
