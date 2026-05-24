"""用户相关视图。

模块说明：提供用户查询、创建、更新、删除、密码重置等接口。
权限体系：基于 admin_level（管理级别）+ position（岗位）三轴模型，不再依赖 Role M2M。
"""

import logging
import os
import uuid
from datetime import datetime, timedelta

from django.db.models import Q, Case, When, IntegerField, Value
from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.storage import default_storage

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from api_v1.models import Department, UserProfile, Config
from api_v1.models.system.position import Position
from api_v1.models.system.user_profile import AdminLevel
from api_v1.serializers import UserSerializer
from api_v1.utils.responses import drf_ok, drf_error
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.image_validator import validate_image_file, resize_image_to_square
from api_v1.utils.avatar_presets import get_random_preset, is_local_upload
from api_v1.services.nc.nc_sync_service import NcSyncService
from api_v1.services.nc.nc_api_client import NcApiClient

logger = logging.getLogger(__name__)


def _dept_subtree(root_id: int) -> set[int]:
    """返回指定部门及其所有子部门的 ID 集合（广度优先遍历）。

    用于部门管理员写权限校验：该管理员可对根部门与子部门内的用户执行写操作。

    Args:
        root_id (int): 根部门 ID。

    Returns:
        set[int]: 包含 root_id 本身及所有层级子部门的 ID 集合。
    """
    result: set[int] = {root_id}
    queue = [root_id]
    while queue:
        pid = queue.pop()
        for cid in Department.objects.filter(parent_id=pid).values_list("id", flat=True):
            if cid not in result:
                result.add(cid)
                queue.append(cid)
    return result


class UserViewSet(viewsets.ViewSet):
    """用户相关接口

    路由前缀：/users
    支持：分页、详情、创建、更新、删除、密码修改/重置、个人资料、下拉选项
    """

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """返回当前登录用户基础信息、角色标识与权限点。

        roles 字段由 admin_level 派生（保持前端兼容格式）：
            COMPANY_ADMIN → ["admin", "ROOT"]
            DEPT_ADMIN    → ["dept_admin"]
            MEMBER        → []
        perms 字段来自 position.menus 关联的 perms 字段聚合。
        """
        user = request.user
        if not user.is_authenticated:
            return drf_error("未登录", status=401)
        profile = getattr(user, "profile", None)

        # 由 admin_level 派生前端角色标识
        level = profile.admin_level if profile else AdminLevel.MEMBER
        if user.is_superuser or level == AdminLevel.COMPANY_ADMIN:
            roles = ["admin", "ROOT"]
        elif level == AdminLevel.DEPT_ADMIN:
            roles = ["dept_admin"]
        else:
            roles = []

        # 聚合 position 关联菜单的权限点
        perms_set: set[str] = set()
        try:
            if profile and profile.position_id:
                from api_v1.models.system.menu import Menu
                menu_qs = Menu.objects.filter(
                    status=True,
                    positions__id=profile.position_id,
                ).exclude(perms="").values_list("perms", flat=True).distinct()
                for raw in menu_qs:
                    for token in str(raw).replace("\n", " ").replace("\t", " ").split(","):
                        token = token.strip()
                        if token:
                            perms_set.add(token)
        except Exception:
            logger.warning("[UserViewSet] [me] 聚合权限点失败", exc_info=True)

        perms = sorted(perms_set)

        def abs_avatar(v: str) -> str:
            """将相对头像路径补齐为绝对 URL。预设头像标识符原样透传，不补 URL。"""
            try:
                if not v:
                    return getattr(settings, "DEFAULT_AVATAR_URL", "") or ""
                # 预设头像标识符（如 preset:06）是前端离线 SVG，不需要补绝对路径
                if str(v).startswith("preset:"):
                    return v
                if str(v).startswith(("http://", "https://")):
                    return v
                base = settings.MEDIA_URL.rstrip("/")
                p = str(v)
                if p.startswith("/media/"):
                    rel = p
                elif p.startswith("media/"):
                    rel = "/" + p
                elif p.startswith("uploads/"):
                    rel = base + "/" + p
                else:
                    rel = p if p.startswith("/") else ("/" + p)
                external = (getattr(settings, "BACKEND_EXTERNAL_URL", "") or "").rstrip("/")
                return (external + rel) if external else request.build_absolute_uri(rel)
            except Exception:
                return v or ""

        resp = drf_ok({
            "userId": user.id,
            "username": user.username,
            "nickname": profile.nickname if profile else "",
            "avatar": abs_avatar(profile.avatar if profile else ""),
            "roles": roles,
            "perms": perms,
            "adminLevel": level,
            "deptId": profile.dept_id if profile else None,
        })
        return resp

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        # 支持 pageNum/pageSize/keywords/status/deptId
        qs = User.objects.all().order_by("id")
        kw = request.query_params.get("keywords")
        if kw:
            # 使用 Q 组合 OR，避免 QuerySet union 在分页 count/slice 时报错
            qs = qs.filter(Q(username__icontains=kw) | Q(email__icontains=kw))
        status = request.query_params.get("status")
        if status is not None:
            qs = qs.filter(is_active=bool(int(status)))
        dept_id = request.query_params.get("deptId")
        if dept_id:
            # 包含所选部门及其所有子部门
            try:
                target_ids = set()
                def collect(did):
                    if did in target_ids:
                        return
                    target_ids.add(did)
                    for cid in Department.objects.filter(parent_id=did).values_list('id', flat=True):
                        collect(cid)
                collect(int(dept_id))
                qs = qs.filter(profile__dept_id__in=list(target_ids))
            except Exception:
                qs = qs.filter(profile__dept_id=dept_id)
        # 创建时间范围过滤（YYYY-MM-DD ~ YYYY-MM-DD）
        ct_range = request.query_params.get("createTime")
        # 支持前端通过 query string 传递两段 createTime[]=start&createTime[]=end 的情况
        start = request.query_params.getlist('createTime[]') or request.query_params.getlist('createTime')
        if isinstance(ct_range, (list, tuple)):
            start = ct_range
        if start and len(start) >= 2 and start[0] and start[1]:
            try:
                dt_start = datetime.strptime(start[0], "%Y-%m-%d")
                dt_end = datetime.strptime(start[1], "%Y-%m-%d") + timedelta(days=1)
                qs = qs.filter(date_joined__gte=dt_start, date_joined__lt=dt_end)
            except Exception:
                pass

        # admin_level data scope filter
        req_user = getattr(request, "user", None)
        if req_user and getattr(req_user, "is_authenticated", False) and not req_user.is_superuser:
            _profile = getattr(req_user, "profile", None)
            level = _profile.admin_level if _profile else AdminLevel.MEMBER
            if level == AdminLevel.COMPANY_ADMIN:
                pass
            elif level == AdminLevel.DEPT_ADMIN:
                # 本部门用户优先展示（可编辑），其余按部门+用户名排列
                _own_dept = _profile.dept_id if _profile else None
                if _own_dept:
                    qs = qs.annotate(
                        _dept_priority=Case(
                            When(profile__dept_id=_own_dept, then=Value(0)),
                            default=Value(1),
                            output_field=IntegerField(),
                        )
                    ).order_by("_dept_priority", "profile__dept__name", "username")
            else:
                qs = qs.filter(pk=req_user.id)
        total, items, _, _ = paginate_queryset(request, qs)
        data = UserSerializer(items, many=True).data
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get"], url_path=r"(?P<user_id>[^/]+)/form")
    def form(self, request, user_id: str):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return drf_error("未找到用户", status=404)
        return drf_ok(UserSerializer(user).data)

    @action(detail=False, methods=["post"], url_path="")
    def create(self, request):
        payload = request.data.copy()
        username = payload.get("username")
        password = payload.get("password") or "123456"
        email = payload.get("email") or ""
        nickname = payload.get("nickname") or ""
        mobile = payload.get("mobile") or ""
        # 若未显式传入 avatar，随机分配系统预设头像（格式 'preset:01'~'preset:12'）
        avatar = payload.get("avatar") or get_random_preset()
        dept_id = payload.get("deptId")
        status_num = payload.get("status", 1)
        gender = payload.get("gender")
        if not username:
            return drf_error("用户名不能为空", status=400)
        if not email:
            return drf_error("邮箱不能为空", status=400)
        if User.objects.filter(username=username).exists():
            return drf_error("用户名已存在", status=400)
        if User.objects.filter(email=email).exists():
            return drf_error("邮箱已被使用", status=400)
        # 写权限检查：部门管理员只能在本部门（含子部门）内创建用户
        if not request.user.is_superuser and dept_id is not None:
            _req_p = getattr(request.user, "profile", None)
            _req_level = _req_p.admin_level if _req_p else AdminLevel.MEMBER
            if _req_level == AdminLevel.DEPT_ADMIN and _req_p and _req_p.dept_id:
                try:
                    if int(dept_id) not in _dept_subtree(_req_p.dept_id):
                        return drf_error("部门管理员只能在本部门内创建用户", status=403)
                except (ValueError, TypeError):
                    pass
        user = User.objects.create(username=username, email=email, is_active=bool(int(status_num)))
        user.set_password(password)
        user.save()
        position_id = payload.get("positionId")
        admin_level_val = payload.get("adminLevel", AdminLevel.MEMBER)
        try:
            admin_level_val = int(admin_level_val)
            if admin_level_val not in AdminLevel.values:
                admin_level_val = AdminLevel.MEMBER
        except (ValueError, TypeError):
            admin_level_val = AdminLevel.MEMBER
        # 权限封顶：请求者无法创建权限高于自身的用户。
        # AdminLevel 数字越小权限越高：COMPANY_ADMIN=1 > DEPT_ADMIN=2 > MEMBER=3
        if not request.user.is_superuser:
            try:
                _req_profile = getattr(request.user, "profile", None)
                _req_level = _req_profile.admin_level if _req_profile else AdminLevel.MEMBER
            except Exception:
                _req_level = AdminLevel.MEMBER
            if admin_level_val < _req_level:
                # 请求创建的级别高于自身，强制降至与自身相同级别
                admin_level_val = _req_level
        profile = UserProfile.objects.create(
            user=user,
            nickname=nickname,
            mobile=mobile,
            avatar=avatar,
            dept_id=dept_id,
            admin_level=admin_level_val,
        )
        if gender is not None:
            try:
                profile.gender = int(gender)
            except (ValueError, TypeError):
                pass
        if position_id:
            try:
                pos = Position.objects.get(pk=position_id)
                if pos.is_builtin:
                    return drf_error("内置岗位不可手动分配给用户", status=400)
                profile.position = pos
            except Position.DoesNotExist:
                pass
        profile.save()
        # extra_nc_groups M2M：仅在前端传 extraGroupIds 时设置（需在 on_user_created 前完成，以便 _enqueue_extra_groups 读到）
        if "extraGroupIds" in payload:
            extra_ids = payload.get("extraGroupIds") or []
            if isinstance(extra_ids, str):
                extra_ids = [s.strip() for s in extra_ids.split(",") if s.strip()]
            try:
                profile.extra_nc_groups.set(extra_ids)
            except Exception as exc:
                logger.warning("[UserViewSet][create] 设置 extra_nc_groups 失败: %s", exc)
        NcSyncService.on_user_created(profile)
        logger.info("[UserViewSet] [create] user=%s", username)
        return drf_ok(UserSerializer(user).data, status=201)

    @action(detail=False, methods=["put"], url_path=r"(?P<id>[^/]+)")
    def update(self, request, id: str):
        try:
            user = User.objects.get(pk=id)
        except User.DoesNotExist:
            return drf_error("未找到用户", status=404)
        # 写权限检查：部门管理员只能编辑本部门（含子部门）的用户
        if not request.user.is_superuser:
            _req_p = getattr(request.user, "profile", None)
            _req_level = _req_p.admin_level if _req_p else AdminLevel.MEMBER
            if _req_level == AdminLevel.DEPT_ADMIN and _req_p and _req_p.dept_id:
                _target_p = getattr(user, "profile", None)
                _target_dept = getattr(_target_p, "dept_id", None)
                if _target_dept is None or _target_dept not in _dept_subtree(_req_p.dept_id):
                    return drf_error("无权编辑其他部门的用户", status=403)
        payload = request.data.copy()
        # 在任何字段被覆写前捕获旧值，以供 NC 同步差量判定
        _old_email = user.email
        _old_is_active = user.is_active
        user.email = payload.get("email", user.email)
        # 保留原值为默认，防止前端未传 status 时意外激活被禁用用户
        new_status = payload.get("status")
        if new_status is not None:
            try:
                user.is_active = bool(int(new_status))
            except (ValueError, TypeError):
                pass
        user.save()
        profile = getattr(user, "profile", None)
        if profile:
            _old_dept_id = profile.dept_id
            _old_display_name = profile.nickname or user.username
            _old_extra_codes = set(profile.extra_nc_groups.values_list("code", flat=True))
            profile.nickname = payload.get("nickname", profile.nickname)
            profile.mobile = payload.get("mobile", profile.mobile)
            profile.avatar = payload.get("avatar", profile.avatar)
            profile.dept_id = payload.get("deptId", profile.dept_id)
            if payload.get("gender") is not None:
                try:
                    profile.gender = int(payload.get("gender"))
                except (ValueError, TypeError):
                    pass
            if "positionId" in payload:
                # admin 账号的岗位绑定不可修改，跳过
                if user.username == "admin":
                    pass
                else:
                    pid = payload.get("positionId")
                    if pid:
                        try:
                            pos = Position.objects.get(pk=pid)
                            if pos.is_builtin:
                                return drf_error("内置岗位不可手动分配给用户", status=400)
                            profile.position = pos
                        except Position.DoesNotExist:
                            pass
                    else:
                        profile.position = None
            _old_admin_level = profile.admin_level
            if "adminLevel" in payload:
                try:
                    lvl = int(payload.get("adminLevel"))
                    if lvl in AdminLevel.values:
                        # 权限封顶：非超级用户不允许将用户级别设置高于自身
                        if not request.user.is_superuser:
                            try:
                                _req_profile = getattr(request.user, "profile", None)
                                _req_level = _req_profile.admin_level if _req_profile else AdminLevel.MEMBER
                            except Exception:
                                _req_level = AdminLevel.MEMBER
                            if lvl < _req_level:
                                # 越权设置，拒绝修改并返回 403
                                return drf_error(
                                    "无权设置高于自身权限的管理级别",
                                    status=403,
                                )
                        profile.admin_level = lvl
                except (ValueError, TypeError):
                    pass
            profile.save()
            # extra_nc_groups M2M 更新（仅当前端传 extraGroupIds 时才处理）
            if "extraGroupIds" in payload:
                extra_ids = payload.get("extraGroupIds") or []
                if isinstance(extra_ids, str):
                    extra_ids = [s.strip() for s in extra_ids.split(",") if s.strip()]
                try:
                    profile.extra_nc_groups.set(extra_ids)
                except Exception as exc:
                    logger.warning("[UserViewSet][update] 设置 extra_nc_groups 失败: %s", exc)
            NcSyncService.on_user_updated(
                profile,
                old_admin_level=_old_admin_level,
                old_dept_id=_old_dept_id,
                old_display_name=_old_display_name,
                old_email=_old_email,
                old_extra_group_codes=_old_extra_codes if "extraGroupIds" in payload else None,
            )
        if user.is_active != _old_is_active:
            NcSyncService.on_user_status_changed(profile, enabled=user.is_active)
        logger.info("[UserViewSet] [update] id=%s", id)
        return drf_ok(UserSerializer(user).data)

    @action(detail=False, methods=["delete"], url_path=r"(?P<id>[^/]+)")
    def delete(self, request, id: str):
        # 支持单个或逗号分隔的批量删除
        try:
            if isinstance(id, str) and "," in id:
                ids = [s.strip() for s in id.split(",") if s.strip()]
            else:
                ids = [id]
            users_qs = User.objects.filter(id__in=ids)
            if not users_qs.exists():
                return drf_error("未找到用户", status=404)
            # 写权限检查：部门管理员只能删除本部门（含子部门）的用户
            if not request.user.is_superuser:
                _req_p = getattr(request.user, "profile", None)
                _req_level = _req_p.admin_level if _req_p else AdminLevel.MEMBER
                if _req_level == AdminLevel.DEPT_ADMIN and _req_p and _req_p.dept_id:
                    _allowed = _dept_subtree(_req_p.dept_id)
                    if users_qs.exclude(profile__dept_id__in=list(_allowed)).exists():
                        return drf_error("无权删除其他部门的用户", status=403)
            count = users_qs.count()
            usernames_del = list(users_qs.values_list("username", flat=True))
            # 先入队 NC disable，再删除 Django 用户（保证 username 在入队时仍有效）
            for uname in usernames_del:
                NcSyncService.on_user_deleted(uname)
            users_qs.delete()
            logger.info("[UserViewSet] [delete] %s, count=%d", usernames_del, count)
            return drf_ok({"deletedCount": count})
        except User.DoesNotExist:
            return drf_error("未找到用户", status=404)
        except Exception:
            return drf_error("服务器内部错误", status=500)



    @action(detail=False, methods=["put"], url_path=r"(?P<id>[^/]+)/password/reset")
    def reset_password(self, request, id: str):
        try:
            user = User.objects.get(pk=id)
        except User.DoesNotExist:
            return drf_error("未找到用户", status=404)
        password = request.query_params.get("password") or "123456"
        user.set_password(password)
        user.save()
        return drf_ok({"message": "password reset"})

    @action(detail=False, methods=["get"], url_path="profile")
    def profile_get(self, request):
        user = request.user
        if not user.is_authenticated:
            return drf_error("未登录", status=401)
        # 补充前端常用聚合字段（与 /users/me 保持一致但包含更详细的角色/部门信息）
        profile = getattr(user, "profile", None)
        dept_name = ""
        if profile and getattr(profile, "dept", None):
            dept_name = profile.dept.name
        data = UserSerializer(user).data
        # 头像补齐为绝对 URL
        try:
            av = data.get('avatar') or ''
            if av and not str(av).startswith(('http://', 'https://')):
                base = settings.MEDIA_URL.rstrip('/')
                if str(av).startswith('/media/'):
                    rel = av
                elif str(av).startswith('media/'):
                    rel = '/' + str(av)
                elif str(av).startswith('uploads/'):
                    rel = base + '/' + str(av)
                else:
                    rel = av if str(av).startswith('/') else ('/' + str(av))
                data['avatar'] = request.build_absolute_uri(rel)
        except Exception:
            pass
        data["deptName"] = dept_name or data.get("deptName", "")
        return drf_ok(data)

    @action(detail=False, methods=["put"], url_path="profile")
    def profile_put(self, request):
        user = request.user
        if not user.is_authenticated:
            return drf_error("未登录", status=401)
        payload = request.data.copy()
        profile = getattr(user, "profile", None)
        if profile:
            profile.nickname = payload.get("nickname", profile.nickname)
            profile.mobile = payload.get("mobile", profile.mobile)
            profile.avatar = payload.get("avatar", profile.avatar)
            profile.dept_id = payload.get("deptId", profile.dept_id)
            profile.save()
        user.email = payload.get("email", user.email)
        user.save()
        return drf_ok(UserSerializer(user).data)

    @action(detail=False, methods=["put"], url_path="password")
    def change_password(self, request):
        user = request.user
        if not user.is_authenticated:
            return drf_error("未登录", status=401)
        payload = request.data.copy()
        old_pwd = payload.get("oldPassword")
        new_pwd = payload.get("newPassword")
        if not user.check_password(old_pwd):
            # write_log removed: 修改密码失败：原密码错误
            return drf_error("原密码错误", status=400)
        user.set_password(new_pwd)
        user.save()
        return drf_ok({"message": "password changed"})

    @action(detail=False, methods=["post"], url_path="avatar")
    def upload_avatar(self, request):
        """上传头像：三重校验 + 服务端压缩 + 原子写 DB + 旧文件清理 + NC 实时同步。

        请求：multipart/form-data，字段名 file（JPEG / PNG / WEBP，≤5MB）
        响应：{ url }  ——  前端拿到 url 后直接更新本地 store，无需再调 updateProfile。
        """
        user = request.user
        if not getattr(user, 'is_authenticated', False):
            return drf_error("未登录", status=401)

        file = request.FILES.get('file')
        if not file:
            return drf_error("未选择文件", status=400)

        # ① Magic Number 三重校验（替代原 content_type 单一校验）
        try:
            ext, _mime = validate_image_file(file, max_mb=5)
        except ValueError as exc:
            return drf_error(str(exc), status=400)

        # ② 服务端居中裁剪 + 压缩至 512×512 JPEG
        try:
            resized_buf = resize_image_to_square(file, size=512)
        except Exception as exc:
            logger.error("[UserViewSet][upload_avatar] 图片处理失败: %s", exc, exc_info=True)
            return drf_error("图片处理失败，请重新选择", status=400)

        resized_bytes = resized_buf.read()
        resized_buf.seek(0)

        # ③ 保存压缩后的头像文件（统一存为 .jpg）
        now = datetime.utcnow()
        rel_path = f"uploads/avatars/{now.year:04d}/{now.month:02d}/{uuid.uuid4().hex}.jpg"
        saved_path = default_storage.save(rel_path, resized_buf)
        media_rel = settings.MEDIA_URL.rstrip('/') + '/' + saved_path.lstrip('/')
        new_url = request.build_absolute_uri(media_rel)

        # ④ 原子写 DB：更新 profile.avatar + 清理旧文件
        profile = getattr(user, 'profile', None)
        old_avatar = profile.avatar if profile else ""
        if profile:
            # 清理旧本地上传文件（预设/外部 URL 跳过，防止误删）
            if is_local_upload(old_avatar):
                try:
                    old_rel = old_avatar
                    # 兼容绝对 URL 格式：提取 /media/ 之后的相对路径
                    if "/media/uploads/" in old_avatar:
                        old_rel = old_avatar.split("/media/")[1]
                    if default_storage.exists(old_rel):
                        default_storage.delete(old_rel)
                        logger.info(
                            "[UserViewSet][upload_avatar] 已清理旧头像文件: %s", old_rel
                        )
                except Exception as exc:
                    logger.warning(
                        "[UserViewSet][upload_avatar] 旧头像清理失败（不阻断）: %s", exc
                    )
            profile.avatar = new_url
            profile.save(update_fields=["avatar"])

        # ⑥ NC 头像同步（管理员级 OCS API，不依赖 nc_app_password，失败仅记录 WARNING 不阻断响应）
        try:
            nc_admin = NcApiClient.from_settings()
            nc_admin.update_user_avatar(user.username, resized_bytes, "image/jpeg")
        except Exception as exc:
            logger.warning(
                "[UserViewSet][upload_avatar] NC 头像同步失败（不阻断）: user=%s err=%s",
                user.username,
                exc,
            )

        logger.info("[UserViewSet][upload_avatar] user=%s 头像更新成功", user.username)
        return drf_ok({"url": new_url})

    # 通用精简图片上传（非头像），供富文本/普通图片组件复用
    @action(detail=False, methods=["post"], url_path="upload-image")
    def upload_image(self, request):
        """精简图片上传接口，不恢复旧文件系统。\n\n        请求: multipart/form-data, 字段 file\n        可选参数: thumbs=64,128,256 (逗号分隔)，若不传使用默认 64,128,256\n        响应: { url, name, width, height, size, thumbs: {"64": url, ...} }\n        限制: 图片 <=2MB, 仅 image/* MIME\n        """
        user = request.user
        # 可选：允许未登录富文本临时上传？此处若要求登录就返回 401
        if not getattr(user, 'is_authenticated', False):
            return drf_error("未登录", status=401)
        file = request.FILES.get('file')
        if not file:
            return drf_error("未选择文件", status=400)
        ctype = getattr(file, 'content_type', '') or ''
        if not ctype.startswith('image/'):
            return drf_error("仅支持图片", status=400)
        if getattr(file, 'size', 0) > 2 * 1024 * 1024:
            return drf_error("图片过大(>2MB)", status=400)
        # 保存原图
        from datetime import datetime
        now = datetime.utcnow()
        ext = os.path.splitext(file.name)[1] or ''
        rel_path = f"uploads/images/{now.year:04d}/{now.month:02d}/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(rel_path, file)
        media_rel = settings.MEDIA_URL.rstrip('/') + '/' + saved_path.lstrip('/')
        base_url = request.build_absolute_uri(media_rel)
        # 读取尺寸
        try:
            from PIL import Image
            file.seek(0)
            img = Image.open(file)
            width, height = img.size
        except Exception:
            width = height = None
        # 生成缩略图
        thumbs_param = request.query_params.get('thumbs') or request.data.get('thumbs')
        sizes = []
        if thumbs_param:
            for tok in str(thumbs_param).split(','):
                tok = tok.strip()
                if tok.isdigit():
                    sizes.append(int(tok))
        if not sizes:
            sizes = [64, 128, 256]
        thumbs = {}
        try:
            if width and height:
                img.load()
                for s in sizes:
                    try:
                        thumb = img.copy()
                        thumb.thumbnail((s, s))
                        t_rel = f"uploads/images/{now.year:04d}/{now.month:02d}/{uuid.uuid4().hex}_{s}{ext or '.jpg'}"
                        from io import BytesIO
                        buf = BytesIO()
                        save_fmt = 'JPEG'
                        if ext.lower() in ('.png', '.gif', '.webp'):
                            save_fmt = ext.replace('.', '').upper()
                        thumb.save(buf, format=save_fmt if save_fmt != 'JPG' else 'JPEG')
                        buf.seek(0)
                        default_storage.save(t_rel, buf)
                        t_rel_url = settings.MEDIA_URL.rstrip('/') + '/' + t_rel.lstrip('/')
                        thumbs[str(s)] = request.build_absolute_uri(t_rel_url)
                    except Exception:
                        continue
        except Exception:
            pass
        # write_log removed: 上传图片(通用)
        return drf_ok({
            "url": base_url,
            "name": os.path.basename(saved_path),
            "width": width,
            "height": height,
            "size": getattr(file, 'size', None),
            "thumbs": thumbs,
            "suggestCrop": {"aspect": "1:1", "recommended": [256, 128, 64]},
        })

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        users = User.objects.filter(is_active=True).order_by("id")
        data = [{"label": u.username, "value": u.id} for u in users]
        return drf_ok(data)

    @staticmethod
    def generic_get(request):
        # 兼容 GET /users -> 返回全部列表（前端主要使用 /users/page）
        users = User.objects.all().order_by("id")
        return drf_ok([UserSerializer(u).data for u in users])


