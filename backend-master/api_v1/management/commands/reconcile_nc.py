"""reconcile_nc：Nextcloud 全量对账管理命令。

对比本地 UserProfile 与 NC 实际状态，补齐缺失的用户/群组成员关系。
适用场景：首次迁移、NC 故障恢复后、人工排查不一致时使用。

用法：
    python manage.py reconcile_nc [--dry-run] [--user <username>]
"""
import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.models.nc.nc_sync_task import NcSyncTask, SyncOperation, SyncStatus
from api_v1.models.system.user_profile import AdminLevel, UserProfile
from api_v1.services.nc.nc_api_client import NcApiClient
from api_v1.services.nc.nc_sync_service import NcSyncService

logger = logging.getLogger(__name__)
User = get_user_model()


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
        """命令入口：执行对账逻辑。

        Args:
            *args: 不使用。
            **options (dict): 命令行选项字典，包含 dry_run / username / execute。

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
                    NcSyncService._enqueue_extra_groups(username, profile)
                    enqueued += 1

            elif not is_active and nc_exists:
                # 需要禁用
                self.stdout.write(f"  → 需禁用 NC 用户: {username}")
                if not dry_run:
                    NcSyncService.enqueue_disable_user(username)
                    enqueued += 1

        # 对账部门 Group Folder：有 NcGroup 但 folder_id 为空的部门
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
        """立即执行所有 PENDING 任务（不经 Celery，适合一次性对账场景）。"""
        pending = list(NcSyncTask.objects.filter(status=SyncStatus.PENDING).order_by("id"))
        self.stdout.write(self.style.NOTICE(f"[reconcile_nc] 开始直接执行 {len(pending)} 条 PENDING 任务..."))
        success = 0
        failed = 0
        for task in pending:
            ok = NcSyncService.execute_task(task)
            if ok:
                success += 1
            else:
                failed += 1
        self.stdout.write(self.style.SUCCESS(
            f"[reconcile_nc] 执行完毕 | success={success} failed={failed}"
        ))
