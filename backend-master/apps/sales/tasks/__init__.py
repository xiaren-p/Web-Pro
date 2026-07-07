"""销售 app 任务注册入口。autodiscover_tasks 只扫描 apps.sales.tasks，此处从子模块重导出。"""
from apps.sales.listing.tasks import (
    upload_listing_images_task,
    run_listing_tag_sync_task,
    run_listing_tag_modify_task,
    run_image_sync_queue_task,
)

__all__ = [
    "upload_listing_images_task",
    "run_listing_tag_sync_task",
    "run_listing_tag_modify_task",
    "run_image_sync_queue_task",
]
