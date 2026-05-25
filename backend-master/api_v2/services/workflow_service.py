"""工作流业务逻辑服务（workflow_service）。

职责：任务并发检查、入队、状态同步、取消操作。
遵循"胖 Service / 瘦 Controller"原则，视图层只负责 HTTP 解析与结果包装。
"""

import logging
from typing import Optional

from django.contrib.auth.models import User
from django.utils import timezone

from api_v2.models.workflow_execution import ExecutionStatus, WorkflowExecution, WorkflowType

logger = logging.getLogger(__name__)

# 工作流类型 → Celery 注册 Task Name 的映射
# 使用字符串延迟导入，避免模块顶层产生循环依赖
_TASK_NAME_MAP: dict[str, str] = {
    WorkflowType.LISTING_IMAGE_UPLOAD: 'api_v2.tasks.listing_image_upload_task.upload_listing_images_task',
}


class WorkflowService:
    """
    工作流服务类。

    负责任务生命周期的全部管理操作：并发检查、入队、状态同步、取消。
    所有方法均为静态方法，无需实例化直接调用。
    """

    @staticmethod
    def get_running_task(workflow_type: str) -> Optional[WorkflowExecution]:
        """
        查询是否存在同类型任务正在执行。

        Args:
            workflow_type (str): 工作流类型，取值见 WorkflowType 枚举。

        Returns:
            Optional[WorkflowExecution]: 正在运行的执行记录，不存在则返回 None。
        """
        return WorkflowExecution.objects.filter(
            workflow_type=workflow_type,
            status__in=[ExecutionStatus.PENDING, ExecutionStatus.RUNNING],
        ).first()

    @staticmethod
    def create_and_enqueue(
        user: User,
        workflow_type: str,
        params: dict,
    ) -> WorkflowExecution:
        """
        创建执行记录并将任务推入 Celery 队列。

        采用"先写库占位再入队"策略：即使入队失败也会将记录标记为 failed，
        避免出现无状态追踪的游离任务。

        Args:
            user (User): 触发该任务的登录用户。
            workflow_type (str): 工作流类型，取值见 WorkflowType 枚举。
            params (dict): 透传给 Celery Task 的业务参数。

        Returns:
            WorkflowExecution: 新建的执行记录对象（status=pending，task_id 已写入）。

        Raises:
            ValueError: 同类型任务已在执行中（并发锁定），或不支持的工作流类型。
            Exception: Celery 入队异常时原始抛出。
        """
        # 并发锁定：同类型任务同时仅允许一个执行
        running = WorkflowService.get_running_task(workflow_type)
        if running:
            raise ValueError(
                f"已有 {workflow_type} 任务正在执行（execution_id={running.id}）"
            )

        task_name = _TASK_NAME_MAP.get(workflow_type)
        if not task_name:
            raise ValueError(f"不支持的工作流类型: {workflow_type}")

        # 预先创建记录占位（状态 pending），确保任务有可追踪的生命周期
        execution = WorkflowExecution.objects.create(
            user=user,
            workflow_type=workflow_type,
            params=params,
            status=ExecutionStatus.PENDING,
        )

        try:
            from celery import current_app

            task = current_app.send_task(
                task_name,
                kwargs={'execution_id': execution.id, **params},
            )

            execution.task_id = task.id
            execution.save(update_fields=['task_id'])

            logger.info(
                "[WorkflowService.create_and_enqueue] 任务已入队: "
                "workflow_type=%s execution_id=%s task_id=%s user=%s",
                workflow_type,
                execution.id,
                task.id,
                user.username,
            )

            return execution

        except Exception as exc:
            execution.status = ExecutionStatus.FAILED
            execution.error_msg = f"任务入队失败: {exc}"
            execution.save(update_fields=['status', 'error_msg'])

            logger.error(
                "[WorkflowService.create_and_enqueue] 入队失败: %s",
                exc,
                exc_info=True,
            )
            raise

    @staticmethod
    def sync_status(execution: WorkflowExecution) -> WorkflowExecution:
        """
        将 Celery 任务的真实状态同步回执行记录。

        仅对 pending/running 状态的记录执行同步，终态记录直接返回。

        Args:
            execution (WorkflowExecution): 待同步的执行记录。

        Returns:
            WorkflowExecution: 同步后的执行记录（如有变化则已保存）。
        """
        terminal_statuses = [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        ]

        if execution.status in terminal_statuses or not execution.task_id:
            return execution

        from celery.result import AsyncResult

        task_result = AsyncResult(execution.task_id)

        if task_result.ready():
            if task_result.successful():
                execution.status = ExecutionStatus.COMPLETED
                execution.result = task_result.result
            else:
                execution.status = ExecutionStatus.FAILED
                execution.error_msg = str(task_result.result)

            execution.completed_at = timezone.now()
            execution.save(update_fields=['status', 'result', 'error_msg', 'completed_at'])

        return execution

    @staticmethod
    def cancel(execution_id: int, user: User) -> WorkflowExecution:
        """
        取消指定的执行任务。

        向 Celery Worker 发送 revoke 指令后将记录状态更新为 cancelled。

        Args:
            execution_id (int): 要取消的执行记录 ID。
            user (User): 请求取消操作的用户（确保只能取消自己的任务）。

        Returns:
            WorkflowExecution: 已更新状态的执行记录。

        Raises:
            WorkflowExecution.DoesNotExist: 执行记录不存在或不属于该用户。
            ValueError: 任务已处于终态，无法取消。
        """
        execution = WorkflowExecution.objects.get(id=execution_id, user=user)

        terminal_statuses = [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        ]

        if execution.status in terminal_statuses:
            raise ValueError("任务已终止，无法取消")

        if execution.task_id:
            from celery.app import current_app

            current_app.control.revoke(execution.task_id, terminate=True)

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = timezone.now()
        execution.save(update_fields=['status', 'completed_at'])

        logger.info(
            "[WorkflowService.cancel] 任务已取消: execution_id=%s user=%s",
            execution_id,
            user.username,
        )

        return execution
