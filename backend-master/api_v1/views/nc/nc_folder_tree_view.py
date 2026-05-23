"""NC 文件夹树视图 ViewSet（nc_folder_tree_view）。

提供基于 WebDAV 的文件夹浏览、新建以及权限规则分配接口，
作为 NC 文件权限配置的交互式管理入口。
"""
from __future__ import annotations

import logging

from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models.nc.nc_file_access_rule import NcFileAccessRule
from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.permissions import MenuPermRequired
from api_v1.serializers.nc.nc_file_rule_serializer import NcFileRuleReadSerializer
from api_v1.services.nc.nc_api_client import NcApiClient
from api_v1.services.nc.nc_sync_service import NcSyncService
from api_v1.utils.responses import drf_error, drf_ok

logger = logging.getLogger(__name__)


class NcFolderTreeViewSet(viewsets.ViewSet):
    """NC 文件夹树与权限管理接口。

    以 DEPT_ADMIN 群组为基础，浏览 Group Folder 文件夹结构，
    并对任意路径进行创建目录和分配 ACL 规则操作。

    权限依托菜单权限体系：
      - 查询：nc:folder:query
      - 新建文件夹：nc:folder:mkdir
      - 设置权限：nc:folder:setperm
      - 删除规则：nc:folder:delete
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
        if action_name in ("group_list", "list_folder", "path_rules", "all_groups") and method == "GET":
            required = ["nc:folder:query"]
        elif action_name == "mkdir" and method == "POST":
            required = ["nc:folder:mkdir"]
        elif action_name == "set_rule" and method == "POST":
            required = ["nc:folder:setperm"]
        elif action_name == "delete_rule" and method == "DELETE":
            required = ["nc:folder:delete"]
        setattr(self, "required_perms", required)
        return super().get_permissions()

    # ------------------------------------------------------------------ #
    #  群组列表（左侧面板数据源）                                            #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["get"], url_path="groups")
    def group_list(self, request: Request):
        """获取所有 DEPT_ADMIN NC 群组列表。

        Returns:
            list[dict]: [{id, code, name, deptName}]，按部门排序顺序排列。
        """
        groups = (
            NcGroup.objects.filter(group_type=NcGroupType.DEPT_ADMIN)
            .select_related("dept")
            .order_by("dept__order_num", "name")
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

    # ------------------------------------------------------------------ #
    #  文件夹树列表（懒加载数据源）                                          #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["get"], url_path="list")
    def list_folder(self, request: Request):
        """列出指定 NC 群组目录下的直属子文件夹（WebDAV PROPFIND Depth:1）。

        Query Params:
            groupId (int): NcGroup ID（必须是 DEPT_ADMIN 类型）。
            path (str): 相对于 Group Folder 挂载点根的子路径；留空代表挂载点根目录。

        Returns:
            dict: {
                mountPoint: str,         # Group Folder 挂载点名称
                currentPath: str,        # 当前浏览路径（相对于挂载点）
                fullNcPath: str,         # = mountPoint/currentPath（NcFileAccessRule.nc_path 格式）
                currentRule: dict|null,  # 当前路径自身的 ACL 规则
                items: [{ name, ncPath, rule }]  # 每个直属子文件夹
            }
        """
        group_id_str = request.query_params.get("groupId")
        sub_path = (request.query_params.get("path") or "").strip("/")

        nc_group, error = _resolve_dept_admin_group(group_id_str)
        if error:
            return drf_error(error)

        client, mount_point, fetch_error = _get_mount_point(nc_group)
        if fetch_error:
            return drf_error(fetch_error)

        dav_path, full_nc_path = _build_dav_path(
            client._admin_user, mount_point, sub_path
        )

        try:
            raw_items = client.list_dav_folder(dav_path)
        except RuntimeError as exc:
            return drf_error(f"读取文件夹列表失败: {exc}")

        # 批量查询该层下已有规则，以 nc_path 为索引加速节点匹配
        rules_map: dict[str, NcFileAccessRule] = {
            r.nc_path: r
            for r in NcFileAccessRule.objects.filter(
                nc_group=nc_group,
                nc_path__startswith=full_nc_path + "/",
            )
        }
        # 当前路径自身的规则（用于顶层配置展示）
        current_rule = NcFileAccessRule.objects.filter(
            nc_group=nc_group,
            nc_path=full_nc_path,
        ).first()

        items = [
            {
                "name": item["name"],
                "ncPath": f"{full_nc_path}/{item['name']}",
                "rule": _serialize_rule(rules_map.get(f"{full_nc_path}/{item['name']}")),
            }
            for item in raw_items
        ]

        return drf_ok({
            "mountPoint": mount_point,
            "currentPath": sub_path,
            "fullNcPath": full_nc_path,
            "currentRule": _serialize_rule(current_rule),
            "items": items,
        })

    # ------------------------------------------------------------------ #
    #  新建文件夹（WebDAV MKCOL）                                          #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["post"], url_path="mkdir")
    def mkdir(self, request: Request):
        """在指定路径下创建新文件夹（WebDAV MKCOL，幂等）。

        Body:
            groupId (int): NcGroup ID（必须是 DEPT_ADMIN 类型）。
            parentPath (str): 新文件夹父路径（相对于挂载点根）；空串=挂载点根。
            folderName (str): 新文件夹名称，不能含 '/'。

        Returns:
            dict: {message, ncPath}。ncPath 为新目录的完整 nc_path。
        """
        group_id_str = str(request.data.get("groupId", ""))
        parent_path = (request.data.get("parentPath") or "").strip("/")
        folder_name = (request.data.get("folderName") or "").strip()

        if not folder_name:
            return drf_error("folderName 不能为空")
        if "/" in folder_name:
            return drf_error("文件夹名称不能包含 '/'")

        nc_group, error = _resolve_dept_admin_group(group_id_str)
        if error:
            return drf_error(error)

        client, mount_point, fetch_error = _get_mount_point(nc_group)
        if fetch_error:
            return drf_error(fetch_error)

        # 构造新目录的 WebDAV 路径与 nc_path
        if parent_path:
            new_dav_path = (
                f"/remote.php/dav/files/{client._admin_user}"
                f"/{mount_point}/{parent_path}/{folder_name}"
            )
            new_nc_path = f"{mount_point}/{parent_path}/{folder_name}"
        else:
            new_dav_path = (
                f"/remote.php/dav/files/{client._admin_user}"
                f"/{mount_point}/{folder_name}"
            )
            new_nc_path = f"{mount_point}/{folder_name}"

        try:
            client.create_dav_folder(new_dav_path)
        except RuntimeError as exc:
            return drf_error(f"创建文件夹失败: {exc}")

        logger.info(
            "[NcFolderTreeViewSet][mkdir] 创建文件夹 ncPath=%s",
            new_nc_path,
        )
        return drf_ok({"message": f"文件夹 '{folder_name}' 创建成功", "ncPath": new_nc_path})

    # ------------------------------------------------------------------ #
    #  设置/更新权限规则（upsert）                                          #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["post"], url_path="set-rule")
    def set_rule(self, request: Request):
        """为指定路径设置或更新 NC ACL 权限规则（update_or_create）。

        Body:
            groupId (int): NcGroup ID。
            ncPath (str): 完整路径（含挂载点），如 "技术部/机密文档"。
            permissionBits (int): 权限位，范围 1~31。
            status (bool, optional): 是否生效，默认 True。

        Returns:
            dict: NcFileRuleReadSerializer 格式的规则数据（更新或新建后的结果）。
        """
        group_id_str = str(request.data.get("groupId", ""))
        nc_path = (request.data.get("ncPath") or "").strip("/")
        permission_bits_raw = request.data.get("permissionBits")
        status = request.data.get("status", True)

        if not nc_path:
            return drf_error("ncPath 不能为空")
        try:
            permission_bits = int(permission_bits_raw)
            if not (1 <= permission_bits <= 31):
                raise ValueError
        except (ValueError, TypeError):
            return drf_error("permissionBits 必须在 1~31 之间")

        try:
            nc_group = NcGroup.objects.select_related("dept").get(pk=int(group_id_str))
        except (NcGroup.DoesNotExist, ValueError, TypeError):
            return drf_error("群组不存在")

        with transaction.atomic():
            rule, created = NcFileAccessRule.objects.update_or_create(
                nc_group=nc_group,
                nc_path=nc_path,
                defaults={
                    "permission_bits": permission_bits,
                    "is_group_folder": True,
                    "status": bool(status),
                },
            )

        logger.info(
            "[NcFolderTreeViewSet][set_rule] %s ncPath=%s permBits=%s",
            "新建" if created else "更新",
            nc_path,
            permission_bits,
        )
        _enqueue_acl_for_rule(rule)
        return drf_ok(NcFileRuleReadSerializer(rule).data)

    # ------------------------------------------------------------------ #
    #  删除权限规则                                                         #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["delete"], url_path=r"rule/(?P<pk>\d+)")
    def delete_rule(self, request: Request, pk: str = "0"):
        """删除指定 NC 权限规则并入队撤销 ACL 同步任务。

        URL Param:
            pk (int): NcFileAccessRule 主键。

        Returns:
            dict: 空 dict。
        """
        try:
            rule = NcFileAccessRule.objects.select_related("nc_group").get(pk=pk)
        except NcFileAccessRule.DoesNotExist:
            return drf_error("规则不存在", code=404)

        nc_path = rule.nc_path
        group_code = rule.nc_group.code
        rule.delete()
        NcSyncService.enqueue_revoke_path_acl(nc_path, group_code)

        logger.info(
            "[NcFolderTreeViewSet][delete_rule] pk=%s ncPath=%s group=%s",
            pk, nc_path, group_code,
        )
        return drf_ok({})

    # ------------------------------------------------------------------ #
    #  查询指定路径上所有群组的规则                                          #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["get"], url_path="path-rules")
    def path_rules(self, request: Request):
        """获取指定 NC 路径上所有群组的 ACL 规则（跨群组聚合）。

        Query Params:
            ncPath (str): 完整路径（含挂载点），如 "销售部/报表"。

        Returns:
            list[dict]: NcFileRuleReadSerializer 格式的规则列表，按部门排序。
        """
        nc_path = (request.query_params.get("ncPath") or "").strip("/")
        if not nc_path:
            return drf_error("ncPath 不能为空")

        rules = (
            NcFileAccessRule.objects
            .filter(nc_path=nc_path)
            .select_related("nc_group", "nc_group__dept")
            .order_by("nc_group__dept__order_num", "nc_group__name")
        )
        return drf_ok(NcFileRuleReadSerializer(rules, many=True).data)

    # ------------------------------------------------------------------ #
    #  获取所有 NC 群组（规则弹窗群组选择器数据源）                           #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["get"], url_path="all-groups")
    def all_groups(self, request: Request):
        """获取所有 NC 群组（不限类型），供添加 ACL 规则时选择目标群组。

        Returns:
            list[dict]: [{id, code, name, groupType, deptName}]，按部门排序。
        """
        groups = (
            NcGroup.objects
            .select_related("dept")
            .order_by("dept__order_num", "group_type", "name")
        )
        result = [
            {
                "id": g.id,
                "code": g.code,
                "name": g.name,
                "groupType": g.group_type,
                "deptName": g.dept.name if g.dept else "",
            }
            for g in groups
        ]
        return drf_ok(result)


# ------------------------------------------------------------------ #
#  私有工具函数                                                         #
# ------------------------------------------------------------------ #

def _resolve_dept_admin_group(
    group_id_str: str | None,
) -> tuple[NcGroup | None, str | None]:
    """解析 groupId 参数，确保其为 DEPT_ADMIN 类型群组。

    Args:
        group_id_str (str | None): 字符串形式的 NcGroup 主键。

    Returns:
        tuple: (NcGroup 实例, 错误信息字符串)；成功时错误信息为 None。
    """
    try:
        nc_group = NcGroup.objects.select_related("dept").get(
            pk=int(group_id_str),  # type: ignore[arg-type]
            group_type=NcGroupType.DEPT_ADMIN,
        )
        return nc_group, None
    except (NcGroup.DoesNotExist, ValueError, TypeError):
        return None, "群组不存在或不是 DEPT_ADMIN 类型"


def _get_mount_point(
    nc_group: NcGroup,
) -> tuple[NcApiClient | None, str, str | None]:
    """根据 DEPT_ADMIN 群组获取对应 Group Folder 的挂载点名称。

    先找同部门的 DEPT 群组取 folder_id，再向 NC 查询挂载点。

    Args:
        nc_group (NcGroup): 目标 DEPT_ADMIN 群组实例。

    Returns:
        tuple: (NcApiClient 实例, mount_point 字符串, 错误信息)；
               成功时错误信息为 None，失败时前两项为 None/"" 。
    """
    dept_ng = NcGroup.objects.filter(
        dept_id=nc_group.dept_id,
        group_type=NcGroupType.DEPT,
    ).first()
    if not dept_ng or not dept_ng.folder_id:
        return None, "", "对应 DEPT 群组缺少 folder_id，请先运行对账任务"

    try:
        client = NcApiClient.from_settings()
        folders = client.list_group_folders()
    except RuntimeError as exc:
        return None, "", f"获取 NC Group Folder 列表失败: {exc}"

    folder_info = folders.get(dept_ng.folder_id)
    if not folder_info:
        return None, "", "NC 中未找到对应 Group Folder，请先运行对账任务"

    mount_point = folder_info.get("mount_point", "").strip("/")
    return client, mount_point, None


def _build_dav_path(
    admin_user: str,
    mount_point: str,
    sub_path: str,
) -> tuple[str, str]:
    """构造 WebDAV 请求路径与 NcFileAccessRule.nc_path 格式的完整路径。

    Args:
        admin_user (str): NC 管理员用户名。
        mount_point (str): Group Folder 挂载点名称（不含首尾斜杠）。
        sub_path (str): 相对于挂载点根的子路径（不含首尾斜杠）；可为空字符串。

    Returns:
        tuple: (dav_path, full_nc_path)。
               dav_path 用于 WebDAV 请求；full_nc_path 用于数据库查询与权限规则保存。
    """
    if sub_path:
        dav_path = (
            f"/remote.php/dav/files/{admin_user}/{mount_point}/{sub_path}/"
        )
        full_nc_path = f"{mount_point}/{sub_path}"
    else:
        dav_path = f"/remote.php/dav/files/{admin_user}/{mount_point}/"
        full_nc_path = mount_point
    return dav_path, full_nc_path


def _serialize_rule(rule: NcFileAccessRule | None) -> dict | None:
    """将 NcFileAccessRule 序列化为精简 dict，返回 None 表示无规则。

    Args:
        rule (NcFileAccessRule | None): 可能为 None 的规则实例。

    Returns:
        dict | None: 序列化后的规则字典，或 None。
    """
    if rule is None:
        return None
    return NcFileRuleReadSerializer(rule).data


def _enqueue_acl_for_rule(rule: NcFileAccessRule) -> None:
    """为规则入队 ENABLE_FOLDER_ACL + SET_PATH_ACL 同步任务。

    folder_id 从同部门 DEPT 类型群组获取，与 reconcile 逻辑保持一致。

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
