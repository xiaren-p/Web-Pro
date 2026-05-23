"""NC 部门群组配置 ViewSet（nc_dept_group_view）。

提供部门与 NC 双群组（DEPT + DEPT_ADMIN）的初始化状态查询和批量补全接口，
用于对账和修复已有部门缺失 NC 群组的情况。
"""
from __future__ import annotations

import logging

from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models import Department
from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.permissions import MenuPermRequired
from api_v1.services.nc.nc_sync_service import NcSyncService
from api_v1.utils.responses import drf_error, drf_ok

logger = logging.getLogger(__name__)


def _provision_dept(dept: Department) -> None:
    """为单个部门幂补所有缺失的 NC 群组记录并入队同步任务（完全幂等）。

    覆盖三种场景：
      1. none  → 创建 DEPT + DEPT_ADMIN 群组并创建 Group Folder
      2. partial（DEPT 存在，DEPT_ADMIN 缺失） → 只建 DEPT_ADMIN
      3. partial（双群组存在但 folder_id 未回写） → 重新入队 folder 创建

    Args:
        dept (Department): 已保存的部门实例。
    """
    base_code = (dept.code or "").strip() or f"dept_{dept.id}"
    admin_code = f"{base_code}_admin"

    with transaction.atomic():
        dept_ng, dept_created = NcGroup.objects.get_or_create(
            dept=dept,
            group_type=NcGroupType.DEPT,
            defaults={"code": base_code, "name": dept.name},
        )
        admin_ng, admin_created = NcGroup.objects.get_or_create(
            dept=dept,
            group_type=NcGroupType.DEPT_ADMIN,
            defaults={"code": admin_code, "name": f"{dept.name}（管理员）"},
        )

    # 入队阶段放在 atomic 块外，避免提交前任务被消费
    if dept_created:
        NcSyncService.enqueue_create_group(dept_ng.code, dept_ng.name)
    if admin_created:
        NcSyncService.enqueue_create_group(admin_ng.code, admin_ng.name)
    # folder_id 为空表示建空任务未执行或失败，重新入队（NC 候幂）
    if dept_ng.folder_id is None:
        NcSyncService.enqueue_create_group_folder(dept_ng.code, dept.name)

    logger.info(
        "[_provision_dept] dept_id=%s dept_created=%s admin_created=%s folder_id=%s",
        dept.id, dept_created, admin_created, dept_ng.folder_id,
    )


def _dept_group_row(dept: Department, groups_by_dept: dict) -> dict:
    """构建单个部门的 NC 群组状态行。

    Args:
        dept (Department): 部门实例。
        groups_by_dept (dict): {dept_id: {group_type: NcGroup}} 映射。

    Returns:
        dict: 包含 deptId、deptName、deptCode、status、deptGroup、adminGroup 的字典。
    """
    pair = groups_by_dept.get(dept.id, {})
    dept_ng: NcGroup | None = pair.get(NcGroupType.DEPT)
    admin_ng: NcGroup | None = pair.get(NcGroupType.DEPT_ADMIN)

    if dept_ng and admin_ng:
        # 双群组都有：若 folder_id 已回写则视为完全就绪，否则视为不完整
        status = "ready" if dept_ng.folder_id else "partial"
    elif dept_ng or admin_ng:
        # 只有其中一个
        status = "partial"
    else:
        status = "none"

    return {
        "deptId": dept.id,
        "deptName": dept.name,
        "deptCode": dept.code or "",
        "status": status,
        "deptGroup": {
            "id": dept_ng.id,
            "code": dept_ng.code,
            "folderId": dept_ng.folder_id,
        } if dept_ng else None,
        "adminGroup": {
            "id": admin_ng.id,
            "code": admin_ng.code,
            "folderId": admin_ng.folder_id,
        } if admin_ng else None,
    }


class NcDeptGroupViewSet(viewsets.ViewSet):
    """NC 部门群组初始化与对账接口。

    以部门为维度，展示每个部门是否已在 NC 完成双群组（DEPT + DEPT_ADMIN）
    初始化，并支持单部门和批量补全操作。

    权限依托菜单权限体系：
      - 查询：nc:group:query
      - 初始化：nc:group:provision
    """

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        """根据 action 与 HTTP 方法动态绑定所需菜单权限码。"""
        action_name = getattr(self, "action", None)
        method = (
            getattr(self.request, "method", "").upper()
            if hasattr(self, "request") else ""
        )
        required: list[str] | None = None
        if action_name == "dept_status" and method == "GET":
            required = ["nc:group:query"]
        elif action_name in ("provision", "provision_all") and method == "POST":
            required = ["nc:group:provision"]
        setattr(self, "required_perms", required)
        return super().get_permissions()

    @action(detail=False, methods=["get"], url_path="")
    def dept_status(self, request: Request):
        """查询所有启用部门的 NC 群组初始化状态。

        Returns:
            {list: DeptGroupRow[]}
        """
        depts = list(
            Department.objects.filter(status=True).order_by("order_num", "id")
        )
        dept_ids = [d.id for d in depts]

        # 一次查询所有 nc_groups，构建 {dept_id: {group_type: NcGroup}} 映射
        nc_groups = NcGroup.objects.filter(
            dept_id__in=dept_ids,
            group_type__in=[NcGroupType.DEPT, NcGroupType.DEPT_ADMIN],
        )
        groups_by_dept: dict[int, dict[str, NcGroup]] = {}
        for ng in nc_groups:
            groups_by_dept.setdefault(ng.dept_id, {})[ng.group_type] = ng

        rows = [_dept_group_row(d, groups_by_dept) for d in depts]
        return drf_ok({"list": rows})

    @action(detail=False, methods=["post"], url_path=r"(?P<dept_id>\d+)/provision")
    def provision(self, request: Request, dept_id: str):
        """为指定部门补全 NC 双群组（幂等，已存在则跳过入队）。

        Args:
            dept_id (str): 部门 ID（URL 路径参数）。

        Returns:
            最新的 DeptGroupRow 状态。
        """
        dept = Department.objects.filter(pk=int(dept_id), status=True).first()
        if not dept:
            return drf_error("部门不存在或已停用", status=404)
        try:
            _provision_dept(dept)
        except Exception as exc:
            logger.error(
                "[NcDeptGroupViewSet][provision] dept_id=%s 初始化失败: %s",
                dept_id, exc, exc_info=True,
            )
            return drf_error(f"初始化失败：{exc}", status=500)

        # 回查最新状态返回给前端
        nc_groups = NcGroup.objects.filter(
            dept_id=dept.id,
            group_type__in=[NcGroupType.DEPT, NcGroupType.DEPT_ADMIN],
        )
        groups_by_dept: dict[int, dict[str, NcGroup]] = {}
        for ng in nc_groups:
            groups_by_dept.setdefault(ng.dept_id, {})[ng.group_type] = ng
        return drf_ok(_dept_group_row(dept, groups_by_dept))

    @action(detail=False, methods=["post"], url_path="provision-all")
    def provision_all(self, request: Request):
        """批量补全所有 status 不为 ready 的部门 NC 双群组（none + partial 均处理）。

        Returns:
            {total: int, success: int, failed: [{deptId, deptName, error}]}
        """
        depts = list(Department.objects.filter(status=True).order_by("order_num", "id"))
        dept_ids = [d.id for d in depts]

        # 构建当前状态映射，判断哪些部门需要处理
        nc_groups = NcGroup.objects.filter(
            dept_id__in=dept_ids,
            group_type__in=[NcGroupType.DEPT, NcGroupType.DEPT_ADMIN],
        )
        groups_by_dept: dict[int, dict[str, NcGroup]] = {}
        for ng in nc_groups:
            groups_by_dept.setdefault(ng.dept_id, {})[ng.group_type] = ng

        # 只跳过真正 ready 的部门（双群组存在且 folder_id 已回写）
        def _is_ready(dept: Department) -> bool:
            pair = groups_by_dept.get(dept.id, {})
            dept_ng = pair.get(NcGroupType.DEPT)
            admin_ng = pair.get(NcGroupType.DEPT_ADMIN)
            return bool(dept_ng and admin_ng and dept_ng.folder_id)

        pending = [d for d in depts if not _is_ready(d)]
        success_count = 0
        failed: list[dict] = []

        for dept in pending:
            try:
                _provision_dept(dept)
                success_count += 1
            except Exception as exc:
                logger.error(
                    "[NcDeptGroupViewSet][provision_all] dept_id=%s 失败: %s",
                    dept.id, exc, exc_info=True,
                )
                failed.append({"deptId": dept.id, "deptName": dept.name, "error": str(exc)})

        return drf_ok({
            "total": len(pending),
            "success": success_count,
            "failed": failed,
        })
