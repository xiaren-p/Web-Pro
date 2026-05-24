"""管理命令：将所有用户头像批量同步至 NC（用户级凭据）。

生产端首次部署 NC 密码安全改造后执行一次，完成以下工作：
  1. 用管理员 API 为每位用户重置一个新的随机 NC 密码
  2. 将新 NC 密码 Fernet 加密后存入 UserProfile.nc_app_password
  3. 读取用户当前头像（预设 → Pillow 生成 PNG；本地上传 → 读取文件）
  4. 以用户自身凭据调用 POST /index.php/avatar 上传头像至 NC

用法示例：
    # 同步所有用户
    python manage.py sync_nc_avatars

    # 只同步指定用户（逗号分隔）
    python manage.py sync_nc_avatars --users alice,bob

    # 演练模式（仅打印操作列表，不执行任何写入）
    python manage.py sync_nc_avatars --dry-run
"""
import logging
import secrets
import string
from typing import Optional

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from api_v1.models.system.user_profile import UserProfile
from api_v1.services.nc.nc_api_client import NcApiClient
from api_v1.utils.avatar_presets import is_local_upload, is_preset, make_preset_png
from api_v1.utils.fernet_crypto import encrypt_value

logger = logging.getLogger(__name__)

_NC_PASSWORD_CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$"


class Command(BaseCommand):
    """批量重置用户 NC 密码并将当前头像同步至 NC（用户级鉴权上传）。"""

    help = "批量重置用户 NC 密码并将当前头像同步至 Nextcloud（用户级凭据上传）"

    def add_arguments(self, parser) -> None:
        """注册命令行参数。"""
        parser.add_argument(
            "--users",
            type=str,
            default="",
            help="逗号分隔的用户名列表（如 alice,bob），留空则处理所有用户",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="演练模式：仅打印将要操作的用户列表，不执行任何写入",
        )

    def handle(self, *args, **options) -> None:
        """命令主体：遍历所有用户，重置 NC 密码并同步头像。

        Args:
            *args: 标准位置参数（由 Django 传入，通常忽略）。
            **options: 命令行选项字典（dry_run / users）。
        """
        dry_run: bool = options["dry_run"]
        users_filter = [u.strip() for u in options["users"].split(",") if u.strip()]

        qs = UserProfile.objects.select_related("user").all()
        if users_filter:
            qs = qs.filter(user__username__in=users_filter)

        total = qs.count()
        self.stdout.write(f"待同步用户数: {total}  dry_run={dry_run}\n")

        # 非演练模式才需要初始化管理员客户端
        admin_client: Optional[NcApiClient] = None
        if not dry_run:
            try:
                admin_client = NcApiClient.from_settings()
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"NC 管理员客户端初始化失败: {exc}"))
                return

        ok = skip = fail = 0

        for profile in qs:
            user = profile.user
            username = user.username
            avatar = profile.avatar or ""

            if dry_run:
                self.stdout.write(f"  [DRY] user={username}  avatar={avatar!r}")
                ok += 1
                continue

            # ① 生成新 NC 密码，通过管理员 API 重置（确保密码已知可保存）
            nc_password = "".join(secrets.choice(_NC_PASSWORD_CHARS) for _ in range(20))
            try:
                admin_client.update_user_password(username, nc_password)  # type: ignore[union-attr]
            except Exception as exc:
                logger.warning("[sync_nc_avatars] NC 密码重置失败: user=%s err=%s", username, exc)
                self.stdout.write(self.style.WARNING(f"  [FAIL] {username}: NC 密码重置失败 {exc}"))
                fail += 1
                continue

            # ② 加密保存新 NC 密码至 UserProfile
            profile.nc_app_password = encrypt_value(nc_password)
            profile.save(update_fields=["nc_app_password"])

            # ③ 获取头像字节（预设生成 PNG；本地上传读取文件；其余跳过）
            avatar_bytes: Optional[bytes] = None
            mime_type = "image/png"

            if is_preset(avatar):
                avatar_bytes = make_preset_png(username, avatar)

            elif is_local_upload(avatar):
                try:
                    rel_path = avatar.split("/media/")[1] if "/media/" in avatar else avatar
                    with default_storage.open(rel_path, "rb") as f:
                        avatar_bytes = f.read()
                    mime_type = "image/jpeg"
                except Exception as exc:
                    logger.warning(
                        "[sync_nc_avatars] 本地头像文件读取失败: user=%s err=%s", username, exc
                    )

            else:
                logger.info(
                    "[sync_nc_avatars] 用户无本地/预设头像，跳过 NC 头像上传: user=%s avatar=%s",
                    username,
                    avatar,
                )
                self.stdout.write(f"  [SKIP] {username}: 无本地头像（NC 密码已更新）")
                skip += 1
                continue

            if avatar_bytes is None:
                self.stdout.write(self.style.WARNING(f"  [SKIP] {username}: 头像字节读取失败"))
                skip += 1
                continue

            # ④ 用管理员凭据上传头像到 NC（admin 级 OCS API，更可靠）
            try:
                admin_client.update_user_avatar(username, avatar_bytes, mime_type)  # type: ignore[union-attr]
                logger.info("[sync_nc_avatars] NC 头像已同步: user=%s", username)
                self.stdout.write(self.style.SUCCESS(f"  [OK] {username}"))
                ok += 1
            except Exception as exc:
                logger.warning("[sync_nc_avatars] NC 头像上传失败: user=%s err=%s", username, exc)
                self.stdout.write(self.style.WARNING(f"  [FAIL] {username}: 头像上传失败 {exc}"))
                fail += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n同步完成  成功={ok}  跳过(无头像)={skip}  失败={fail}  共={total}"
            )
        )
