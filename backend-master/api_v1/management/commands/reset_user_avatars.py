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
import io
import logging

from django.core.management.base import BaseCommand

from api_v1.models.system.user_profile import UserProfile
from api_v1.utils.avatar_presets import get_random_preset, is_local_upload, is_preset

logger = logging.getLogger(__name__)

# 12 个预设与前端 avatarPresets.ts backgroundColor 数组一一对应
_PRESET_COLORS: dict = {
    "preset:01": "5c6bc0",
    "preset:02": "42a5f5",
    "preset:03": "26c6da",
    "preset:04": "66bb6a",
    "preset:05": "ffa726",
    "preset:06": "ef5350",
    "preset:07": "ab47bc",
    "preset:08": "26a69a",
    "preset:09": "8d6e63",
    "preset:10": "78909c",
    "preset:11": "ec407a",
    "preset:12": "7e57c2",
}


def _make_preset_png(username: str, preset_id: str) -> bytes:
    """用 Pillow 生成与前端预设色匹配的头像，返回 PNG bytes。

    正方形背景使用与前端 @dicebear/thumbs 相同的 12 色调色板，
    圆心绘制用户名首字母（大写白色）。生成 256×256 PNG。

    Args:
        username (str): Django 用户名，取首字母作为头像文字。
        preset_id (str): 预设标识符，如 'preset:06'，用于查调色板。

    Returns:
        bytes: PNG 二进制，可直接传给 NcApiClient.update_user_avatar()。
    """
    from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

    size = 256
    hex_color = _PRESET_COLORS.get(preset_id, "5c6bc0")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # 正方形画布（NC 会自动裁圆）
    img = Image.new("RGB", (size, size), (r, g, b))
    draw = ImageDraw.Draw(img)

    # 首字母
    letter = (username[0] if username else "U").upper()
    font_size = 110
    try:
        # Pillow >= 10.0 支持 load_default(size=)
        font = ImageFont.load_default(size=font_size)  # type: ignore[call-arg]
    except TypeError:
        font = ImageFont.load_default()

    # 居中绘制
    bbox = draw.textbbox((0, 0), letter, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]
    draw.text((x, y), letter, fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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
            help="将新预设头像同步到 Nextcloud：后端用 Pillow 生成与前端色调一致的 PNG 并 POST 上传",
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
                    png_bytes = _make_preset_png(username, new_preset)
                    nc_client.update_user_avatar(username, png_bytes, mime_type="image/png")
                    nc_ok += 1
                    logger.info(
                        "[reset_user_avatars] NC 头像已上传: user=%s preset=%s",
                        username,
                        new_preset,
                    )
                except Exception as exc:
                    nc_fail += 1
                    logger.warning(
                        "[reset_user_avatars] NC 同步失败: user=%s reason=%s",
                        username,
                        exc,
                    )
                    self.stderr.write(f"  NC 同步失败 {username}: {exc}")

        # 结果摘要
        self.stdout.write(self.style.SUCCESS(
            f"\n[reset_user_avatars] 完成。"
            f"处理={processed}，跳过={skipped}"
            + (f"，NC成功={nc_ok}，NC失败={nc_fail}" if nc_sync else "")
            + ("（演练模式，未实际写入）" if dry_run else "")
        ))
