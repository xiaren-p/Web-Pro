"""NC 文件访问规则 ViewSet（nc_file_access_rule）。"""
from __future__ import annotations

from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models.nc.nc_file_access_rule import NcFileAccessRule
from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.permissions import MenuPermRequired
from api_v1.serializers.nc.nc_file_rule_serializer import (
    NcFileRuleReadSerializer,
    NcFileRuleWriteSerializer,
)
from api_v1.services.nc.nc_sync_service import NcSyncService
from api_v1.utils.responses import drf_error, drf_ok


class NcFileRuleViewSet(viewsets.ViewSet):
    """NC 文件路径 ACL 规则管理接口。

    权限依托菜单权限体系：
      - 查询：nc:rule:query
      - 新增：nc:rule:add
      - 编辑：nc:rule:edit
      - 删除：nc:rule:delete
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
        if action_name == "page" and method == "GET":
            required = ["nc:rule:query"]
        elif action_name == "group_options" and method == "GET":
            required = ["nc:rule:query"]
        elif action_name == "create_rule" and method == "POST":
            required = ["nc:rule:add"]
        elif action_name == "update_or_delete" and method == "PUT":
            required = ["nc:rule:edit"]
        elif action_name == "update_or_delete" and method == "DELETE":
            required = ["nc:rule:delete"]
        setattr(self, "required_perms", required)
        return super().get_permissions()

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request: Request):
        """分页查询 NC 文件访问规则列表。

        Query Params:
            page (int): 页码，默认 1。
            pageSize (int): 每页条数，默认 20。
            ncGroupId (int, optional): 按群组 ID 筛选。
            status (str, optional): "true"/"false" 按是否生效筛选。

        Returns:
            dict: {total, list[NcFileRuleReadSerializer]}
        """
        qs = NcFileAccessRule.objects.select_related("nc_group").order_by("nc_group_id", "nc_path")

        nc_group_id = request.query_params.get("ncGroupId")
        if nc_group_id:
            try:
                qs = qs.filter(nc_group_id=int(nc_group_id))
            except (ValueError, TypeError):
                return drf_error("ncGroupId 参数无效")

        status_param = request.query_params.get("status")
        if status_param is not None:
            qs = qs.filter(status=(status_param.lower() == "true"))

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("pageSize", 20))))
        except (ValueError, TypeError):
            return drf_error("分页参数无效")

        total = qs.count()
        offset = (page - 1) * page_size
        records = qs[offset: offset + page_size]
        serializer = NcFileRuleReadSerializer(records, many=True)
        return drf_ok({"total": total, "list": serializer.data})

    @action(detail=False, methods=["get"], url_path="group-options")
    def group_options(self, request: Request):
        """获取可选的 NC 群组列表（DEPT_ADMIN 类型）用于前端下拉。

        Returns:
            list[dict]: [{id, code, name, deptName}]
        """
        groups = (
            NcGroup.objects.filter(group_type=NcGroupType.DEPT_ADMIN)
            .select_related("dept")
            .order_by("name")
        )
        result = [
            {
                "id": g.id,
                "code": g.code,
                "name": g.name,
                "deptName": g.dept.name if g.dept else "",
            }
            for g in groups
        ]
        return drf_ok(result)

    @action(detail=False, methods=["post"], url_path="create")
    def create_rule(self, request: Request):
        """新建 NC 文件访问规则。

        Body:
            ncGroupId (int): 目标 NcGroup ID（DEPT_ADMIN 群组）。
            ncPath (str): 子路径，首尾斜杠自动去除。
            permissionBits (int): 权限位（1-31）。
            isGroupFolder (bool, optional): 默认 True。
            status (bool, optional): 默认 True。

        Returns:
            dict: 新建成功的规则读序列化结果。
        """
        serializer = NcFileRuleWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return drf_error(str(serializer.errors))

        with transaction.atomic():
            rule: NcFileAccessRule = serializer.save()

        # 入队 ACL 同步任务
        self._enqueue_acl_for_rule(rule)
        return drf_ok(NcFileRuleReadSerializer(rule).data)

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<pk>\d+)")
    def update_or_delete(self, request: Request, pk: str = "0"):
        """更新或删除指定 NC 文件访问规则。

        PUT Body:
            同 create_rule Body（ncGroupId 可选）。
        DELETE:
            无需 Body；删除前先入队撤销 ACL。

        Args:
            pk (str): NcFileAccessRule 主键。

        Returns:
            dict: 更新成功时返回更新后的规则读序列化结果；删除成功返回空 dict。
        """
        try:
            rule = NcFileAccessRule.objects.select_related("nc_group__dept").get(pk=pk)
        except NcFileAccessRule.DoesNotExist:
            return drf_error("规则不存在", code=404)

        if request.method == "DELETE":
            # 先撤销 ACL，再删除记录（保留 nc_path 和 group code 用于撤销）
            NcSyncService.enqueue_revoke_path_acl(rule.nc_path, rule.nc_group.code)
            rule.delete()
            return drf_ok({})

        # PUT：更新规则
        serializer = NcFileRuleWriteSerializer(rule, data=request.data, partial=True)
        if not serializer.is_valid():
            return drf_error(str(serializer.errors))

        with transaction.atomic():
            updated_rule: NcFileAccessRule = serializer.save()

        # 重新入队 ACL 同步（覆盖写）
        self._enqueue_acl_for_rule(updated_rule)
        return drf_ok(NcFileRuleReadSerializer(updated_rule).data)

    # ------------------------------------------------------------------ #
    #  私有辅助方法                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _enqueue_acl_for_rule(rule: NcFileAccessRule) -> None:
        """为指定规则入队 ENABLE_FOLDER_ACL + SET_PATH_ACL 任务。

        folder_id 从 DEPT 群组取（与 reconcile 逻辑保持一致）。

        Args:
            rule (NcFileAccessRule): 已保存的规则实例。
        """
        folder_id: int | None = None
        if rule.nc_group.dept_id:
            dept_ng = NcGroup.objects.filter(
                dept_id=rule.nc_group.dept_id,
                group_type=NcGroupType.DEPT,
            ).first()
            if dept_ng:
                folder_id = dept_ng.folder_id

        if folder_id:
            NcSyncService.enqueue_enable_folder_acl(folder_id)
        NcSyncService.enqueue_set_path_acl(rule)
