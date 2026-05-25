"""api_v2 Celery 任务包。"""

from api_v2.tasks.listing_image_upload_task import upload_listing_images_task

__all__ = [
    'upload_listing_images_task',
]
