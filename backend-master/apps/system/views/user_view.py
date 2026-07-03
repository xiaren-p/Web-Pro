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

from apps.system.models import Department, UserProfile, Config
from apps.system.models.position import Position
from apps.system.models.user_profile import AdminLevel
from apps.system.serializers import UserSerializer
from apps.common.utils.responses import drf_ok, drf_error
from apps.common.utils.pagination import paginate_queryset
from apps.common.utils.image_validator import validate_image_file, resize_image_to_square
from apps.system.utils.avatar_presets import get_random_preset, is_local_upload, is_preset, make_preset_png
from apps.nc.services.nc_sync_service import NcSyncService
from apps.nc.services.nc_api_client import NcApiClient

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
    """UserViewSet 视图集。"""
    permission_classes = [IsAuthenticated]
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
                from apps.system.models.menu import Menu
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
        """分页列表查询。"""
        qs = User.objects.all().select_related("profile", "profile__dept", "profile__position").order_by("id")
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
                    """递归收集部门及其所有子部门 ID 到外层集合。

Args:
    did (int): 起始部门 ID。

Returns:
    None: 结果累积到外层 target_ids 集合。
"""
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
        """获取表单详情。"""
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return drf_error("未找到用户", status=404)
        return drf_ok(UserSerializer(user).data)

    @action(detail=False, methods=["post"], url_path="")
    def create(self, request):
        """创建资源。"""
        from apps.system.services.user_write_service import create_user
        user, err = create_user(request, request.data)
        if err:
            return drf_error(err[0], status=err[1])
        return drf_ok(UserSerializer(user).data, status=201)

    @action(detail=False, methods=["put"], url_path=r"(?P<id>[^/]+)")
    def update(self, request, id: str):
        """更新用户。"""
        from apps.system.services.user_write_service import update_user
        user, err = update_user(request, id, request.data)
        if err:
            return drf_error(err[0], status=err[1])
        return drf_ok(UserSerializer(user).data)

    @action(detail=False, methods=["delete"], url_path=r"(?P<id>[^/]+)")
    def delete(self, request, id: str):
        """删除用户。"""
        if isinstance(id, str) and "," in id:
            ids = [s.strip() for s in id.split(",") if s.strip()]
        else:
            ids = [id]
        from apps.system.services.user_write_service import delete_users
        _, err = delete_users(request, ids)
        if err:
            return drf_error(err[0], status=err[1])
        return drf_ok({"deletedCount": len(ids)})



    @action(detail=False, methods=["put"], url_path=r"(?P<id>[^/]+)/password/reset")
    def reset_password(self, request, id: str):
        """密码重置/修改。"""
        try:
            user = User.objects.get(pk=id)
        except User.DoesNotExist:
            return drf_error("未找到用户", status=404)
        password = request.query_params.get("password") or ""
        user.set_password(password)
        user.save()
        return drf_ok({"message": "password reset"})

    @action(detail=False, methods=["get"], url_path="profile")
    def profile_get(self, request):
        """用户个人资料获取/更新。"""
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
        """用户个人资料获取/更新。"""
        user = request.user
        if not user.is_authenticated:
            return drf_error("未登录", status=401)
        payload = request.data.copy()
        profile = getattr(user, "profile", None)
        # 保存前记录旧值，用于 NC 同步对比
        _old_display_name = (profile.nickname if profile and profile.nickname else user.username)
        _old_email = user.email or ""
        if profile:
            _old_avatar = profile.avatar or ""
            profile.nickname = payload.get("nickname", profile.nickname)
            profile.mobile = payload.get("mobile", profile.mobile)
            profile.avatar = payload.get("avatar", profile.avatar)
            profile.dept_id = payload.get("deptId", profile.dept_id)
            if payload.get("gender") is not None:
                profile.gender = int(payload.get("gender"))
            profile.save()
            # 切换了预设头像时，将 Pillow 生成的 PNG 同步至 NC
            _new_avatar = profile.avatar or ""
            if _new_avatar != _old_avatar and is_preset(_new_avatar):
                try:
                    import secrets as _secrets
                    import string as _string
                    from apps.common.utils.fernet_crypto import encrypt_value as _encrypt

                    _nc_pwd = profile.get_nc_password() or ""
                    if not _nc_pwd:
                        _chars = _string.ascii_letters + _string.digits + "!@#$"
                        _nc_pwd = "".join(_secrets.choice(_chars) for _ in range(20))
                        NcApiClient.from_settings().update_user_password(user.username, _nc_pwd)
                        profile.nc_app_password = _encrypt(_nc_pwd)
                        profile.save(update_fields=["nc_app_password"])

                    _png = make_preset_png(user.username, _new_avatar)
                    NcApiClient.for_user(user.username, _nc_pwd).upload_own_avatar(_png, "image/png")
                except Exception as exc:
                    logger.warning(
                        "[UserViewSet][profile_put] NC 头像同步失败（不阻断）: user=%s err=%s",
                        user.username,
                        exc,
                    )
        user.email = payload.get("email", user.email)
        user.save()
        # NC 同步：昵称或邮箱有变更时入队（不阻断主流程）
        if profile:
            try:
                NcSyncService.on_user_updated(
                    profile,
                    old_display_name=_old_display_name,
                    old_email=_old_email,
                )
            except Exception as exc:
                logger.warning(
                    "[UserViewSet][profile_put] NC 同步入队失败（不阻断）: user=%s err=%s",
                    user.username,
                    exc,
                )
        return drf_ok(UserSerializer(user).data)

    @action(detail=False, methods=["put"], url_path="password")
    def change_password(self, request):
        """密码重置/修改。"""
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

        # ⑥ NC 头像同步（用户凭据，必要时通过管理员 API 先重置密码，失败仅记录 WARNING 不阻断响应）
        try:
            import secrets as _secrets
            import string as _string
            from apps.common.utils.fernet_crypto import encrypt_value as _encrypt

            _nc_pwd = (profile.get_nc_password() if profile else "") or ""
            if not _nc_pwd:
                # nc_app_password 未设置：通过管理员 API 重置一个随机密码并存入库
                _chars = _string.ascii_letters + _string.digits + "!@#$"
                _nc_pwd = "".join(_secrets.choice(_chars) for _ in range(20))
                NcApiClient.from_settings().update_user_password(user.username, _nc_pwd)
                if profile:
                    profile.nc_app_password = _encrypt(_nc_pwd)
                    profile.save(update_fields=["nc_app_password"])

            NcApiClient.for_user(user.username, _nc_pwd).upload_own_avatar(resized_bytes, "image/jpeg")
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
        """获取下拉选项。"""
        users = User.objects.filter(is_active=True).order_by("id")
        data = [{"label": u.username, "value": u.id} for u in users]
        return drf_ok(data)

    @staticmethod
    def generic_get(request):
        # 兼容 GET /users -> 返回全部列表（前端主要使用 /users/page）
        """兼容 GET /users 直接返回全部用户列表。

Args:
    request: DRF Request 对象。

Returns:
    Response: 全部用户序列化数据响应。
"""
        users = User.objects.all().select_related("profile", "profile__dept", "profile__position").order_by("id")
        return drf_ok([UserSerializer(u).data for u in users])


