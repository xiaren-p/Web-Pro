"""管理命令：扫描上传目录，清理超过指定天数且未被任何记录引用的孤儿文件。

覆盖目录：
  - media/uploads/avatars/**   （头像上传）
  - media/uploads/images/**    （通用图片上传）

引用来源（参考集合）：
  - UserProfile.avatar          （头像字段，绝对 URL 或相对路径）

用法示例：
    # 演练模式（只打印，不删除）
    python manage.py cleanup_orphan_uploads --dry-run

    # 清理超过 30 天（默认）的孤儿文件
    python manage.py cleanup_orphan_uploads

    # 自定义保留天数（7 天宽限期）
    python manage.py cleanup_orphan_uploads --days=7

    # 同时清理 avatars 和 images 两个目录
    python manage.py cleanup_orphan_uploads --dirs=avatars,images
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from api_v1.models.system.user_profile import UserProfile

logger = logging.getLogger(__name__)

# 默认保留天数：超过此天数且未被引用的文件才会被删除
_DEFAULT_KEEP_DAYS = 30


class Command(BaseCommand):
    """清理上传目录中超过保留期限且未被任何记录引用的孤儿文件。"""

    help = "清理上传目录中超过保留天数且未被任何引用的孤儿文件（头像/通用图片）"

    def add_arguments(self, parser):
        """注册命令行参数。"""
        parser.add_argument(
            "--days",
            type=int,
            default=_DEFAULT_KEEP_DAYS,
            help=f"孤儿文件最小保留天数（默认 {_DEFAULT_KEEP_DAYS} 天）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="演练模式：仅打印待删除文件，不执行删除",
        )
        parser.add_argument(
            "--dirs",
            default="avatars,images",
            help="要扫描的子目录（逗号分隔），相对于 MEDIA_ROOT/uploads/，默认 avatars,images",
        )

    def handle(self, *args, **options):
        """命令主体：收集引用集合 → 扫描文件 → 对比删除。"""
        keep_days = options["days"]
        dry_run = options["dry_run"]
        scan_dirs = [d.strip() for d in options["dirs"].split(",") if d.strip()]

        media_root = settings.MEDIA_ROOT
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=keep_days)

        self.stdout.write(
            f"[cleanup_orphan_uploads] 开始扫描，保留天数={keep_days}，"
            f"截止时间={cutoff.strftime('%Y-%m-%d %H:%M:%S UTC')}，"
            f"演练模式={'是' if dry_run else '否'}"
        )

        # ① 收集所有被引用的文件相对路径（归一化为 uploads/... 格式）
        referenced = self._collect_referenced_paths()
        self.stdout.write(f"  引用文件数（全库）: {len(referenced)}")

        total_scanned = 0
        total_orphan = 0
        total_deleted = 0
        total_size_bytes = 0

        for sub_dir in scan_dirs:
            scan_root = os.path.join(media_root, "uploads", sub_dir)
            if not os.path.isdir(scan_root):
                self.stdout.write(f"  目录不存在，跳过: {scan_root}")
                continue

            self.stdout.write(f"  扫描目录: {scan_root}")

            for dirpath, _dirs, files in os.walk(scan_root):
                for fname in files:
                    abs_path = os.path.join(dirpath, fname)
                    total_scanned += 1

                    # 转为相对于 media_root 的路径（storage 引用格式）
                    rel_path = os.path.relpath(abs_path, media_root).replace("\\", "/")

                    # 判断是否在引用集合中（精确匹配或 URL 后缀匹配）
                    if self._is_referenced(rel_path, referenced):
                        continue

                    # 检查文件修改时间是否超过截止
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(abs_path), tz=timezone.utc)
                    except OSError:
                        continue

                    if mtime > cutoff:
                        # 文件较新，保留（宽限期内）
                        continue

                    # 确认为孤儿文件
                    total_orphan += 1
                    try:
                        file_size = os.path.getsize(abs_path)
                    except OSError:
                        file_size = 0
                    total_size_bytes += file_size

                    age_days = (datetime.now(tz=timezone.utc) - mtime).days
                    self.stdout.write(
                        f"    孤儿文件: {rel_path}  "
                        f"({file_size // 1024}KB, {age_days}天前)"
                    )

                    if not dry_run:
                        try:
                            default_storage.delete(rel_path)
                            total_deleted += 1
                            logger.info(
                                "[cleanup_orphan_uploads] 已删除孤儿文件: %s (%d bytes)",
                                rel_path,
                                file_size,
                            )
                        except Exception as exc:
                            logger.warning(
                                "[cleanup_orphan_uploads] 删除失败: %s err=%s", rel_path, exc
                            )

        size_mb = total_size_bytes / 1024 / 1024
        self.stdout.write(self.style.SUCCESS(
            f"\n[cleanup_orphan_uploads] 完成。"
            f"扫描={total_scanned}，孤儿={total_orphan}，"
            f"释放约={size_mb:.2f}MB"
            + (f"，已删除={total_deleted}" if not dry_run else "（演练模式，未实际删除）")
        ))

    # ------------------------------------------------------------------ #
    #  内部辅助方法                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _collect_referenced_paths() -> set[str]:
        """收集所有被数据库记录引用的上传文件路径（归一化为 uploads/... 格式）。

        Returns:
            set[str]: 归一化路径集合，元素格式如 'uploads/avatars/2024/12/abc123.jpg'。
        """
        referenced: set[str] = set()

        # UserProfile.avatar：可能是绝对 URL 或相对路径
        for avatar in UserProfile.objects.values_list("avatar", flat=True):
            if not avatar:
                continue
            # 预设标识跳过
            if avatar.startswith("preset:"):
                continue
            norm = Command._normalize_path(avatar)
            if norm:
                referenced.add(norm)

        return referenced

    @staticmethod
    def _normalize_path(avatar: str) -> str | None:
        """将 avatar 字段值转换为 uploads/... 相对路径格式（storage key）。

        Args:
            avatar (str): DB 中存储的头像字段值（绝对 URL 或相对路径）。

        Returns:
            str | None: 归一化路径；若无法识别为本地上传文件则返回 None。
        """
        if not avatar:
            return None
        # 绝对 URL：提取 /media/ 后的部分
        if "/media/uploads/" in avatar:
            idx = avatar.index("/media/") + len("/media/")
            return avatar[idx:]
        # 已是相对路径
        if avatar.startswith("uploads/"):
            return avatar
        return None

    @staticmethod
    def _is_referenced(rel_path: str, referenced: set[str]) -> bool:
        """判断给定的相对路径是否在引用集合中。

        Args:
            rel_path (str): 相对于 MEDIA_ROOT 的文件路径（正斜杠格式）。
            referenced (set[str]): 已归一化的引用路径集合。

        Returns:
            bool: True 表示该文件仍被引用，不应删除。
        """
        if rel_path in referenced:
            return True
        # 容错匹配：以文件名（basename）做二次查找（防止绝对/相对路径格式差异）
        basename = rel_path.split("/")[-1]
        return any(basename in ref for ref in referenced)
