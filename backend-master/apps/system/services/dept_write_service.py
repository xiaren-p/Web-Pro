"""部门写操作业务服务。

封装部门的创建、更新（含循环引用检测）、批量删除逻辑，
并协调 Nextcloud 群组同步。
"""
import logging

from apps.system.models import Department
from apps.nc.services.nc_sync_service import NcSyncService

logger = logging.getLogger(__name__)


def create_dept(name: str, parent_id, sort: int, status, code: str) -> Department:
    """创建部门并触发 NC 群组同步。

    Args:
        name (str): 部门名称。
        parent_id: 父部门 ID，可为 None。
        sort (int): 排序号。
        status: 状态（1=启用, 0=禁用）。
        code (str): 部门编码。

    Returns:
        Department: 新创建的部门实例。
    """
    dept = Department.objects.create(
        name=name or "",
        parent=Department.objects.filter(pk=parent_id).first() if parent_id else None,
        order_num=int(sort or 0),
        code=code or "",
        status=bool(int(status)) if isinstance(status, (str, int)) else bool(status),
    )
    NcSyncService.on_dept_created(dept)
    return dept


def update_dept(dept_id: str, payload: dict) -> tuple:
    """更新部门（带循环引用检测）并触发 NC 同步。

    Args:
        dept_id (str): 部门 ID 字符串。
        payload (dict): 更新字段字典。

    Returns:
        tuple: ``(Department, None)`` 成功；``(None, (error_msg, status_code))`` 失败。
    """
    try:
        d = Department.objects.get(pk=dept_id)
    except Department.DoesNotExist:
        return (None, ("未找到部门", 404))

    d.name = payload.get("name", d.name)
    parent_id = payload.get("parentId")

    if parent_id:
        try:
            pid_int = int(parent_id)
        except Exception:
            pid_int = None
        if pid_int and pid_int == d.id:
            return (None, ("上级部门不能为自身", 400))
        new_parent = Department.objects.filter(pk=parent_id).first()
        cur = new_parent
        while cur is not None:
            if cur.id == d.id:
                return (None, ("上级部门不能为其子孙节点", 400))
            cur = cur.parent
        d.parent = new_parent
    else:
        d.parent = None

    if "sort" in payload:
        d.order_num = int(payload.get("sort") or 0)
    if "code" in payload:
        d.code = payload.get("code") or ""
    if "status" in payload:
        s = payload.get("status")
        d.status = bool(int(s)) if isinstance(s, (str, int)) else bool(s)

    d.save()
    NcSyncService.on_dept_updated(d)
    return (d, None)


def delete_depts(ids: str) -> None:
    """批量删除部门并入队 NC 群组删除。

    NC 同步失败不阻断部门删除主流程，仅记录日志。

    Args:
        ids (str): 逗号分隔的部门 ID 字符串。
    """
    id_list = [i for i in ids.split(",") if i]
    for dept_id in id_list:
        try:
            NcSyncService.on_dept_deleted(int(dept_id))
        except Exception as exc:
            logger.warning(
                "[DeptWriteService] dept_id=%s NC 同步入队失败（部门仍会删除）: %s",
                dept_id, exc, exc_info=True,
            )
    Department.objects.filter(id__in=id_list).delete()
