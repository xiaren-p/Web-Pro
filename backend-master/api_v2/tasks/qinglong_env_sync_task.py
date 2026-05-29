"""青龙面板环境变量定时同步任务（qinglong_env_sync_task）。

Celery Beat 配置（已在 settings.py 中注册）：
    'qinglong-env-sync': {
        'task': 'api_v2.tasks.qinglong_env_sync_task.sync_qinglong_env_task',
        'schedule': 600.0,   # 每 10 分钟执行一次
    }

任务职责：
  调用 QinglongEnvService.refresh_all() 拉取青龙面板中的
  LX_ERP_HEADERS / LX_ADS_HEADERS / MIDDLE_API_HEADERS
  三个环境变量并写入 Django Cache，供各业务模块直接消费。
"""
import logging

from celery import shared_task

from api_v2.services.qinglong_env_service import refresh_all

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="api_v2.tasks.qinglong_env_sync_task.sync_qinglong_env_task",
    queue="parallel_queue",
    max_retries=0,
    soft_time_limit=60,
    time_limit=90,
)
def sync_qinglong_env_task(self) -> dict:
    """定时同步青龙面板环境变量到 Django Cache。

    每 10 分钟由 Celery Beat 触发一次。拉取成功后将以下变量以 TTL=600s 写入缓存：
      - LX_ERP_HEADERS
      - LX_ADS_HEADERS
      - MIDDLE_API_HEADERS

    青龙接入配置从系统参数（Config 模型）读取，配置项：
      - QINGLONG_URL         青龙面板地址
      - QINGLONG_CLIENT_ID   OpenAPI client_id
      - QINGLONG_CLIENT_SECRET OpenAPI client_secret（加密存储）

    Args:
        self: Celery Task 实例（bind=True）。

    Returns:
        dict: {"synced": [已同步的变量名列表], "count": 同步成功数量}。
    """
    logger.info("[sync_qinglong_env_task] 开始同步青龙环境变量")
    result = refresh_all()
    synced = list(result.keys())
    logger.info(
        "[sync_qinglong_env_task] 同步完成: synced=%s count=%d",
        synced,
        len(synced),
    )
    return {"synced": synced, "count": len(synced)}
