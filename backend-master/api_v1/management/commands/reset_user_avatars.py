"""管理命令：为所有用户随机重新分配系统预设头像，并实时同步到 NC。

用法示例：
    # 仅为"没有头像"或"使用外部默认头像"的用户分配预设（安全模式）
    python manage.py reset_user_avatars

    # 同时覆盖已上传自定义头像的用户（强制全量重置）
    python manage.py reset_user_avatars --force

    # 仅打印将要操作的列表，不执行写入（演练模式）
    python manage.py reset_user_avatars --dry-run

    # 重置后同步到 NC
    python manage.py reset_user_avatars --nc-sync

    # 全量覆盖 + NC 同步
    python manage.py reset_user_avatars --force --nc-sync
"""
import logging

from django.core.management.base import BaseCommand

from api_v1.models.system.user_profile import UserProfile
from api_v1.utils.avatar_presets import get_random_preset, is_local_upload, is_preset, make_preset_png

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """为所有用户随机分配系统预设头像（可选同步 NC）。"""

    help = "为所有用户随机重置系统预设头像，并可选实时同步到 Nextcloud"

    def add_arguments(self, parser):
        """注册命令行参数。"""
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="同时覆盖已上传自定义头像的用户；默认仅处理空头像/外部默认头像",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="演练模式：仅打印操作计划，不执行写入",
        )
        parser.add_argument(
            "--nc-sync",
            action="store_true",
            default=False,
            help=(
                "尝试将预设头像同步到 Nextcloud（POST 上传 PNG）。"
                "若 NC 实例不支持管理员为其他用户设置头像（返回 405），"
                "则自动降级为跳过（nc_skip），NC 仍显示自动生成的默认彩色头像。"
            ),
        )

    def handle(self, *args, **options):
        """命令主体：遍历用户 Profile，按规则分配预设头像。"""
        force = options["force"]
        dry_run = options["dry_run"]
        nc_sync = options["nc_sync"]

        profiles = UserProfile.objects.select_related("user").all()
        total = profiles.count()
        self.stdout.write(f"[reset_user_avatars] 共找到 {total} 个用户 Profile")

        processed = 0
        skipped = 0
        nc_ok = 0
        nc_fail = 0
        nc_skip = 0  # NC 端点不支持（405）时的降级计数

        # 仅在需要 NC 同步时才初始化客户端
        nc_client = None
        if nc_sync and not dry_run:
            try:
                from api_v1.services.nc.nc_api_client import NcApiClient
                nc_client = NcApiClient.from_settings()
            except Exception as exc:
                self.stderr.write(f"[reset_user_avatars] NC 客户端初始化失败，将跳过同步: {exc}")
                nc_client = None

        for profile in profiles:
            username = profile.user.username
            current_avatar = profile.avatar or ""

            # 判断是否需要处理该用户
            should_reset = False
            if not current_avatar:
                # 无头像 → 总是分配
                should_reset = True
            elif is_preset(current_avatar):
                # 已是预设 → 重新随机（洗牌）
                should_reset = True
            elif is_local_upload(current_avatar):
                # 已有自定义上传头像 → 仅 --force 时处理
                should_reset = force
            else:
                # 外部 URL（旧默认头像等）→ 总是替换为预设
                should_reset = True

            if not should_reset:
                skipped += 1
                self.stdout.write(f"  跳过 {username}（已有自定义上传头像，使用 --force 可覆盖）")
                continue

            new_preset = get_random_preset()

            if dry_run:
                self.stdout.write(f"  [dry-run] {username}: {current_avatar!r} → {new_preset!r}")
                processed += 1
                continue

            # 写入数据库
            profile.avatar = new_preset
            profile.save(update_fields=["avatar"])
            processed += 1
            self.stdout.write(f"  已更新 {username}: {new_preset!r}")

            # NC 同步：用 Pillow 生成与前端同色调的 PNG，通过 POST 上传。
            # NC OCS API 支持 POST 上传头像（/ocs/v1.php/cloud/users/{user}/avatar），
            # 但不支持管理员 DELETE 其他用户头像（返回 405），故只做上传不做删除。
            if nc_client:
                try:
                    png_bytes = make_preset_png(username, new_preset)
                    nc_client.update_user_avatar(username, png_bytes, mime_type="image/png")
                    nc_ok += 1
                    logger.info(
                        "[reset_user_avatars] NC 头像已上传: user=%s preset=%s",
                        username,
                        new_preset,
                    )
                except Exception as exc:
                    # 405 = NC 不允许管理员设置其他用户头像（API 设计限制，非配置错误）
                    # NC 会自动为该用户显示默认彩色首字母头像，业务上可接受，降级为跳过
                    if "405" in str(exc):
                        nc_skip += 1
                        logger.info(
                            "[reset_user_avatars] NC 头像同步不支持 (405)，已降级跳过: user=%s"
                            "  → NC 将自动显示默认头像",
                            username,
                        )
                    else:
                        nc_fail += 1
                        logger.warning(
                            "[reset_user_avatars] NC 同步失败: user=%s reason=%s",
                            username,
                            exc,
                        )
                        self.stderr.write(f"  NC 同步失败 {username}: {exc}")

        # 结果摘要
        nc_summary = ""
        if nc_sync:
            nc_summary = f"，NC成功={nc_ok}，NC跳过(405)={nc_skip}，NC失败={nc_fail}"
        self.stdout.write(self.style.SUCCESS(
            f"\n[reset_user_avatars] 完成。"
            f"处理={processed}，跳过={skipped}"
            + nc_summary
            + ("（演练模式，未实际写入）" if dry_run else "")
        ))
