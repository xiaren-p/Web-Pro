"""NC 文件夹树视图 ViewSet（nc_folder_tree_view）。

提供基于 WebDAV 的文件夹浏览、新建以及权限规则分配接口，
作为 NC 文件权限配置的交互式管理入口。
"""
from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.db import models, transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models.nc.nc_file_access_rule import NcFileAccessRule
from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.models.nc.nc_sync_task import NcSyncTask
from api_v1.models.system.department import Department
from api_v1.models.system.user_profile import AdminLevel
from api_v1.permissions import MenuPermRequired
from api_v1.serializers.nc.nc_file_rule_serializer import NcFileRuleReadSerializer
from api_v1.services.nc.nc_api_client import NcApiClient
from api_v1.services.nc.nc_sync_service import NcSyncService
from api_v1.utils.responses import drf_error, drf_ok

User = get_user_model()
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
        if action_name in ("group_list", "list_folder", "path_rules", "user_tree") and method == "GET":
            required = ["nc:folder:query"]
        elif action_name == "mkdir" and method == "POST":
            required = ["nc:folder:mkdir"]
        elif action_name in ("set_rule", "set_rules_batch") and method == "POST":
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
        """获取调用方有权管理的 DEPT_ADMIN NC 群组列表。

        公司管理员返回全量；部门管理员只返回自身部门及子部门对应的群组。

        Returns:
            list[dict]: [{id, code, name, deptName}]，按部门排序顺序排列。
        """
        qs = (
            NcGroup.objects.filter(group_type=NcGroupType.DEPT_ADMIN)
            .select_related("dept")
            .order_by("dept__order_num", "name")
        )
        allowed = _get_caller_dept_ids(request.user)
        if allowed is not None:
            qs = qs.filter(dept_id__in=list(allowed))
        result = [
            {
                "id": g.id,
                "code": g.code,
                "name": g.name,
                "deptName": g.dept.name if g.dept else "",
            }
            for g in qs
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
        scope_error = _check_group_scope(request.user, nc_group)
        if scope_error:
            return drf_error(scope_error, code=403)

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
        rules_map: dict[str, NcFileAccessRule] = {}
        for r in NcFileAccessRule.objects.filter(
            nc_path__startswith=full_nc_path + "/",
        ).select_related("user", "user__profile", "user__profile__dept"):
            rules_map[r.nc_path] = r
        # 当前路径自身的规则（用于顶层配置展示）
        current_rule = NcFileAccessRule.objects.filter(
            nc_path=full_nc_path,
        ).select_related("user", "user__profile", "user__profile__dept").first()

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
        scope_error = _check_group_scope(request.user, nc_group)
        if scope_error:
            return drf_error(scope_error, code=403)

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
        body_data = request.data
        user_id_str = str(body_data.get("userId", ""))
        nc_path = (body_data.get("ncPath") or "").strip("/")
        permission_bits_raw = body_data.get("permissionBits")
        status = body_data.get("status", True)
        group_id_str = str(body_data.get("groupId", ""))

        if not nc_path:
            return drf_error("ncPath 不能为空")

        # 校验调用方是否有权限操作该群组对应的目录
        nc_group, grp_error = _resolve_dept_admin_group(group_id_str)
        if grp_error:
            return drf_error(grp_error)
        scope_error = _check_group_scope(request.user, nc_group)
        if scope_error:
            return drf_error(scope_error, code=403)
        try:
            permission_bits = int(permission_bits_raw)
            if not (1 <= permission_bits <= 31):
                raise ValueError
        except (ValueError, TypeError):
            return drf_error("permissionBits 必须在 1~31 之间")

        try:
            target_user = User.objects.select_related(
                "profile", "profile__dept"
            ).get(pk=int(user_id_str))
        except (User.DoesNotExist, ValueError, TypeError):
            return drf_error("用户不存在")

        with transaction.atomic():
            rule, created = NcFileAccessRule.objects.update_or_create(
                user=target_user,
                nc_path=nc_path,
                defaults={
                    "permission_bits": permission_bits,
                    "status": bool(status),
                },
            )

        logger.info(
            "[NcFolderTreeViewSet][set_rule] %s ncPath=%s user=%s permBits=%s",
            "新建" if created else "更新",
            nc_path,
            target_user.username,
            permission_bits,
        )
        rule.user = target_user  # 确保实例上已经载入关联对象
        _enqueue_acl_for_rule(rule, nc_group)
        return drf_ok(NcFileRuleReadSerializer(rule).data)

    # ------------------------------------------------------------------ #
    #  批量设置权限规则                                                      #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["post"], url_path="set-rules-batch")
    def set_rules_batch(self, request: Request):
        """批量为多个用户设置同一 NC 路径的 ACL 权限规则（update_or_create）。

        支持一次传入多个用户 ID，每个用户对指定路径执行 upsert。
        常用于批量授权（如一次性为某部门所有成员添加访问权限）。

        Body:
            groupId (int): NcGroup ID（用于作用域校验）。
            ncPath (str): 完整路径（含挂载点），如 "技术部/机密文档"。
            userIds (list[int]): 目标用户 ID 列表，不可为空。
            permissionBits (int): 权限位，范围 1~31。
            status (bool, optional): 是否生效，默认 True。

        Returns:
            dict: { created: int, updated: int, rules: [...] }
        """
        body = request.data
        group_id_str = str(body.get("groupId", ""))
        nc_path = (body.get("ncPath") or "").strip("/")
        user_ids = body.get("userIds") or []
        permission_bits_raw = body.get("permissionBits")
        status = body.get("status", True)

        if not nc_path:
            return drf_error("ncPath 不能为空")
        if not isinstance(user_ids, list) or not user_ids:
            return drf_error("userIds 不能为空")

        nc_group, grp_error = _resolve_dept_admin_group(group_id_str)
        if grp_error:
            return drf_error(grp_error)
        scope_error = _check_group_scope(request.user, nc_group)
        if scope_error:
            return drf_error(scope_error, code=403)

        try:
            permission_bits = int(permission_bits_raw)
            if not (1 <= permission_bits <= 31):
                raise ValueError
        except (ValueError, TypeError):
            return drf_error("permissionBits 必须在 1~31 之间")

        # 批量解析用户，过滤非法 ID
        valid_ids = [int(uid) for uid in user_ids if str(uid).lstrip("-").isdigit()]
        users = list(
            User.objects.select_related("profile", "profile__dept").filter(pk__in=valid_ids)
        )
        if not users:
            return drf_error("未找到有效用户")

        created_count = 0
        updated_count = 0
        saved_rules: list[NcFileAccessRule] = []

        with transaction.atomic():
            for target_user in users:
                rule, created = NcFileAccessRule.objects.update_or_create(
                    user=target_user,
                    nc_path=nc_path,
                    defaults={
                        "permission_bits": permission_bits,
                        "status": bool(status),
                    },
                )
                rule.user = target_user
                saved_rules.append(rule)
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        for rule in saved_rules:
            _enqueue_acl_for_rule(rule, nc_group)

        logger.info(
            "[NcFolderTreeViewSet][set_rules_batch] ncPath=%s 新建=%d 更新=%d",
            nc_path,
            created_count,
            updated_count,
        )
        return drf_ok({
            "created": created_count,
            "updated": updated_count,
            "rules": NcFileRuleReadSerializer(saved_rules, many=True).data,
        })

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
            rule = NcFileAccessRule.objects.select_related("user").get(pk=pk)
        except NcFileAccessRule.DoesNotExist:
            return drf_error("规则不存在", code=404)

        nc_path = rule.nc_path
        username = rule.user.username
        target_user = rule.user
        mount_point = nc_path.split("/")[0]
        rule.delete()

        last_task_id = NcSyncTask.objects.order_by("-id").values_list("id", flat=True).first() or 0
        NcSyncService.enqueue_revoke_path_acl(nc_path, username)

        # 若该用户在此文件夹已无剩余规则，撤销根路径屏蔽层并移出 DEPT 群组
        has_remaining = NcFileAccessRule.objects.filter(
            user=target_user,
        ).filter(
            models.Q(nc_path=mount_point) | models.Q(nc_path__startswith=mount_point + "/")
        ).exists()
        if not has_remaining:
            # 1. 撤销根路径屏蔽层（mask=0 展透，移除 ACL 条目）
            NcSyncService.enqueue_revoke_path_acl(mount_point, username)
            # 2. 将用户移出 DEPT 群组（撤销文件夹入口可见性）
            try:
                _nc_client = NcApiClient.from_settings()
                _folders = _nc_client.list_group_folders()
                _folder_id = next(
                    (
                        fid
                        for fid, info in _folders.items()
                        if info.get("mount_point", "").strip("/") == mount_point
                    ),
                    None,
                )
                if _folder_id:
                    dept_ng = NcGroup.objects.filter(
                        group_type=NcGroupType.DEPT,
                        folder_id=_folder_id,
                    ).first()
                    if dept_ng:
                        NcSyncService.enqueue_remove_from_group(username, dept_ng.code)
            except RuntimeError:
                logger.warning(
                    "[NcFolderTreeViewSet][delete_rule] 查询 NC Group Folder 列表失败，跳过 remove_from_group"
                )

        NcSyncService._flush_tasks_after(last_task_id)
        logger.info(
            "[NcFolderTreeViewSet][delete_rule] pk=%s ncPath=%s user=%s",
            pk, nc_path, username,
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
            .select_related("user", "user__profile", "user__profile__dept")
            .order_by("user__profile__dept__order_num", "user__username")
        )
        return drf_ok(NcFileRuleReadSerializer(rules, many=True).data)

    # ------------------------------------------------------------------ #
    #  用户树（添加规则弹窗用户选择器数据源）                         #
    # ------------------------------------------------------------------ #

    @action(detail=False, methods=["get"], url_path="user-tree")
    def user_tree(self, request: Request):
        """返回按部门树组织的用户列表，供添加规则弹窗的用户选择器使用。

        Returns:
            list[dict]: [
                {
                    "id": 1,
                    "name": "技术部",
                    "type": "dept",
                    "children": [
                        {"id": 101, "username": "zhangsan", "nickname": "张三", "type": "user"}
                    ]
                }
            ]
        """
        from api_v1.models.system.user_profile import UserProfile

        # 取有权管理的活跃用户（部门管理员只能看自身部门及子部门的用户）
        allowed = _get_caller_dept_ids(request.user)
        user_qs = UserProfile.objects.filter(user__is_active=True)
        if allowed is not None:
            user_qs = user_qs.filter(dept_id__in=list(allowed))
        profiles = (
            user_qs
            .select_related("user", "dept")
            .order_by("dept__order_num", "dept_id", "user__username")
        )

        # 按部门分组构建树结构
        dept_map: dict[int | None, dict] = {}
        result: list[dict] = []

        for profile in profiles:
            dept = profile.dept
            dept_key = dept.id if dept else None

            if dept_key not in dept_map:
                dept_node: dict = {
                    "id": dept_key,
                    "name": dept.name if dept else "无部门",
                    "type": "dept",
                    "children": [],
                }
                dept_map[dept_key] = dept_node
                result.append(dept_node)

            dept_map[dept_key]["children"].append({
                "id": profile.user_id,
                "username": profile.user.username,
                "nickname": profile.nickname or profile.user.username,
                "type": "user",
            })

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


def _enqueue_acl_for_rule(rule: NcFileAccessRule, nc_group: NcGroup) -> None:
    """为规则入队一系列 NC 同步任务。

    采用“根路径屏蔽 + 指定路径授权”双层 ACL 策略：

    1. 将用户加入部门 DEPT 群组（确保用户能在 Files 中看到文件夹入口）。
    2. 开启 Group Folder ACL 模式（幂等）。
    3. 若是该用户在此文件夹的**第一条**规则，在根路径（mount_point）设置 permissions=0
       的屏蔽层：用户能看到文件夹图标，但无法浏览根目录内容。
    4. 在指定子路径设置实际授权（ACL 少数为节、深层优先）。

    这样用户只能访问明确赋权的路径，而不会看到同文件夹下其他部门 / 同事的文件。

    Args:
        rule (NcFileAccessRule): 已保存的规则实例（nc_path 必须包含挂载点前缀）。
        nc_group (NcGroup): 请求上下文中的 DEPT_ADMIN 群组。
    """
    dept_ng = NcGroup.objects.filter(
        group_type=NcGroupType.DEPT,
        dept_id=nc_group.dept_id,
    ).first()

    from api_v1.models.nc.nc_sync_task import NcSyncTask  # noqa: PLC0415 避免循环导入
    last_task_id = NcSyncTask.objects.order_by("-id").values_list("id", flat=True).first() or 0

    if dept_ng:
        if dept_ng.folder_id:
            # 开启 ACL 模式（幂等），必须在 set_path_acl 之前执行
            NcSyncService.enqueue_enable_folder_acl(dept_ng.folder_id)

        # 判断是否是该用户在此文件夹的第一条规则
        mount_point = rule.nc_path.split("/")[0]
        existing_count = NcFileAccessRule.objects.filter(
            user=rule.user,
        ).filter(
            models.Q(nc_path=mount_point) | models.Q(nc_path__startswith=mount_point + "/")
        ).count()
        is_first_rule = existing_count == 1  # 当前规则已入库，故 ==1 表示没有其他规则

        if is_first_rule:
            # 加入 DEPT 群组：确保用户在 NC Files 中能看到文件夹入口（幂等）
            NcSyncService.enqueue_add_to_group(rule.user.username, dept_ng.code)
            # 根路径屏蔽层：用户能看到文件夹图标但无法浏览根目录，防止看到全公司文件
            NcSyncService.enqueue_set_path_acl_raw(mount_point, rule.user.username, permissions=0)

    NcSyncService.enqueue_set_path_acl(rule)
    # 立即通过后台线程执行，不依赖 Celery Beat 每 30 秒轮询
    NcSyncService._flush_tasks_after(last_task_id)


def _get_caller_dept_ids(user) -> set[int] | None:
    """返回调用方有权管理的部门 ID 集合。

    Args:
        user: Django 登录用户对象（request.user）。

    Returns:
        None  → 公司管理员 / superuser，不受部门限制。
        set   → DEPT_ADMIN 可管辖的部门 ID（含自身及所有子部门）。
        空集  → 普通成员，无权操作任何群组。
    """
    if user.is_superuser:
        return None
    profile = getattr(user, "profile", None)
    if profile is None:
        return set()
    level = profile.admin_level
    if level == AdminLevel.COMPANY_ADMIN:
        return None
    if level == AdminLevel.DEPT_ADMIN and profile.dept_id:
        dept_ids: set[int] = set()

        def _collect(did: int) -> None:
            if did in dept_ids:
                return
            dept_ids.add(did)
            for cid in Department.objects.filter(parent_id=did).values_list("id", flat=True):
                _collect(cid)

        _collect(profile.dept_id)
        return dept_ids
    return set()


def _check_group_scope(user, nc_group: NcGroup) -> str | None:
    """校验调用方是否有权操作指定 NC 群组。

    Args:
        user: Django 登录用户对象。
        nc_group (NcGroup): 被操作的 DEPT_ADMIN 群组。

    Returns:
        None    → 有权限，可继续操作。
        str     → 无权限，错误提示文字。
    """
    allowed = _get_caller_dept_ids(user)
    if allowed is None:
        return None
    if nc_group.dept_id not in allowed:
        return "无权限操作该部门的群组文件夹"
    return None
