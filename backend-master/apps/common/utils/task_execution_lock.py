"""任务执行锁工具（task_execution_lock）。

用于 single_thread_queue 类任务的"任务执行期独占"语义：
    - 视图层调度任务前，调用 ``is_task_running(key)`` 提前判断是否有同类任务在跑
    - 任务体内部用 ``TaskExecutionLock`` 上下文管理器在执行期独占锁

为什么不能用 cache.add 在视图层抢锁后入队：
    cache.add 写动作会真的占着锁直到下面 cache.delete，
    若视图入队后立刻 delete，锁失效，达不到"任务跑期间拒绝调度"的效果；
    若视图保留锁等任务跑完，HTTP 请求会被挂住几十分钟，体验灾难。
    所以视图层应当只 "读"（is_task_running），任务体内才 "占" + "释放"。

典型用法：
    # 1. 视图层
    from apps.common.utils.task_execution_lock import is_task_running, BUSY_RESPONSE
    if is_task_running('bid_adjustment_lock'):
        return Response(BUSY_RESPONSE('竞价调整任务正在执行中'), status=409)
    task = run_bid_adjustment_task.delay()

    # 2. 任务体
    from apps.common.utils.task_execution_lock import TaskExecutionLock
    @shared_task(...)
    def run_bid_adjustment_task(self):
        with TaskExecutionLock('bid_adjustment_lock', ttl=960) as acquired:
            if not acquired:
                logger.warning('[run_bid_adjustment_task] 锁被占，跳过')
                return {...}
            # 跑业务
"""
from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)


def is_task_running(lock_key: str) -> bool:
    """判断指定任务执行锁是否被占用（视图层只读检查）。

    Args:
        lock_key (str): Redis 锁的 key。

    Returns:
        bool: True 表示当前有同类任务在执行（视图层应据此返回 409）；
              False 表示无任务在执行（视图层可继续入队）。
    """
    return cache.get(lock_key) is not None


def BUSY_RESPONSE(msg: str) -> dict[str, Any]:
    """生成"任务正在执行中"的标准响应体（与项目 B0001 业务错误码格式一致）。

    Args:
        msg (str): 给前端展示的中文提示。

    Returns:
        dict: 标准响应字典，配合 status=409 一起返回。
    """
    return {"code": "B0001", "data": None, "msg": msg}


class TaskExecutionLock(AbstractContextManager):
    """任务执行锁上下文管理器（任务体内使用）。

    使用 ``cache.add`` 实现 setnx 语义，进入 ``with`` 块时尝试占锁，
    退出时（无论正常或异常）调用 ``cache.delete`` 释放。
    被 SIGKILL 强杀时 finally 不会执行，依赖 TTL 自然过期作兜底。

    Examples:
        >>> with TaskExecutionLock('my_task_lock', ttl=900) as acquired:
        ...     if not acquired:
        ...         return {'skipped': True}
        ...     do_work()
    """

    def __init__(self, lock_key: str, ttl: int) -> None:
        """初始化任务执行锁。

        Args:
            lock_key (str): Redis 锁 key，必须与视图层 ``is_task_running`` 使用同一 key。
            ttl (int): 锁的过期时间（秒），必须 ≥ 任务 ``time_limit`` + 60 秒缓冲。
                例如任务 time_limit=900，则 ttl 应 ≥ 960。
        """
        self._lock_key = lock_key
        self._ttl = ttl
        self._acquired = False

    def __enter__(self) -> bool:
        """进入上下文，尝试占锁。

        Returns:
            bool: True 表示成功占锁可以执行业务；False 表示已被占应跳过。
        """
        self._acquired = cache.add(self._lock_key, "1", timeout=self._ttl)
        return self._acquired

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文，释放锁。

        仅当本次成功占锁时才释放，避免误删别人占的锁
        （正常情况下 cache.add 拿不到时不会进入临界区，但保险起见加判断）。
        """
        if self._acquired:
            try:
                cache.delete(self._lock_key)
            except Exception as exc:
                logger.error(
                    '[TaskExecutionLock][__exit__] 释放锁失败但不影响业务: key=%s err=%s',
                    self._lock_key,
                    str(exc),
                    exc_info=True,
                )
