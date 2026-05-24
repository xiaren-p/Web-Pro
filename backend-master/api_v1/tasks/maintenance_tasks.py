"""运维维护类 Celery 任务（maintenance_tasks）。

Task 职责：
- cleanup_orphan_uploads：扫描 media/uploads/ 目录，删除超出保留期且不被任何
  UserProfile 引用的孤儿文件，防止磁盘无限膨胀。

Celery Beat 推荐配置（已在 settings.py 中注册）：
    'cleanup-orphan-uploads': 每天凌晨 03:00 (Asia/Shanghai) 自动执行。
"""
import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(
    name="api_v1.tasks.maintenance_tasks.cleanup_orphan_uploads",
    bind=True,
    max_retries=0,
    ignore_result=True,
)
def cleanup_orphan_uploads(self, days: int = 30) -> None:  # type: ignore[override]
    """定时清理孤儿上传文件。

    调用 cleanup_orphan_uploads 管理命令扫描 uploads/avatars 等目录，
    删除保留期超过 days 天且未被任何 UserProfile.avatar 引用的文件。

    Args:
        days (int): 文件最短保留天数，默认 30 天。超过此期限才有资格被删除。
    """
    logger.info("[maintenance_tasks] [cleanup_orphan_uploads] 开始执行，保留天数=%d", days)
    try:
        call_command("cleanup_orphan_uploads", days=days)
        logger.info("[maintenance_tasks] [cleanup_orphan_uploads] 执行完毕")
    except Exception as exc:
        logger.error(
            "[maintenance_tasks] [cleanup_orphan_uploads] 执行失败：%s",
            str(exc),
            exc_info=True,
        )
        raise
