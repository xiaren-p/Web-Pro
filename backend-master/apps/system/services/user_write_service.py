"""用户写操作业务服务。

封装用户创建、更新、删除、密码重置等写操作编排逻辑。
ViewSet 层仅负责请求解析与响应装配。
"""
import logging

from django.contrib.auth.models import User

from apps.system.models import Department, UserProfile, Position
from apps.system.models.user_profile import AdminLevel
from apps.system.utils.avatar_presets import get_random_preset
from apps.nc.services.nc_sync_service import NcSyncService

logger = logging.getLogger(__name__)


def create_user(request, payload: dict):
    """创建用户及关联 UserProfile，同步 NC 群组。

    Args:
        request: DRF request 对象（用于权限校验）。
        payload (dict): 前端提交的创建参数。

    Returns:
        tuple: ``(User, None)`` 成功；``(None, (error_msg, status_code))`` 失败。
    """
    from apps.system.utils.dept_scope import get_dept_subtree

    username = payload.get("username")
    password = payload.get("password") or "123456"
    email = payload.get("email") or ""
    nickname = payload.get("nickname") or ""
    mobile = payload.get("mobile") or ""
    avatar = payload.get("avatar") or get_random_preset()
    dept_id = payload.get("deptId")
    status_num = payload.get("status", 1)
    gender = payload.get("gender")

    if not username:
        return (None, ("用户名不能为空", 400))
    if not email:
        return (None, ("邮箱不能为空", 400))
    if User.objects.filter(username=username).exists():
        return (None, ("用户名已存在", 400))
    if User.objects.filter(email=email).exists():
        return (None, ("邮箱已被使用", 400))

    if not request.user.is_superuser and dept_id is not None:
        _req_p = getattr(request.user, "profile", None)
        _req_level = _req_p.admin_level if _req_p else AdminLevel.MEMBER
        if _req_level == AdminLevel.DEPT_ADMIN and _req_p and _req_p.dept_id:
            try:
                if int(dept_id) not in get_dept_subtree(_req_p.dept_id):
                    return (None, ("部门管理员只能在本部门内创建用户", 403))
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

    if not request.user.is_superuser:
        try:
            _req_profile = getattr(request.user, "profile", None)
            _req_level = _req_profile.admin_level if _req_profile else AdminLevel.MEMBER
        except Exception:
            _req_level = AdminLevel.MEMBER
        if admin_level_val < _req_level:
            admin_level_val = _req_level

    profile = UserProfile.objects.create(
        user=user, nickname=nickname, mobile=mobile, avatar=avatar,
        dept_id=dept_id, admin_level=admin_level_val,
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
                return (None, ("内置岗位不可手动分配给用户", 400))
            profile.position = pos
        except Position.DoesNotExist:
            pass

    profile.save()

    if "extraGroupIds" in payload:
        extra_ids = payload.get("extraGroupIds") or []
        if isinstance(extra_ids, str):
            extra_ids = [s.strip() for s in extra_ids.split(",") if s.strip()]
        try:
            profile.extra_nc_groups.set(extra_ids)
        except Exception as exc:
            logger.warning("[UserWriteService][create] 设置 extra_nc_groups 失败: %s", exc)

    NcSyncService.on_user_created(profile)
    logger.info("[UserWriteService][create] user=%s", username)
    return (user, None)


def update_user(request, user_id: str, payload: dict):
    """更新用户及关联 UserProfile，同步 NC 变更。

    Args:
        request: DRF request 对象（用于权限校验）。
        user_id (str): 用户 ID。
        payload (dict): 前端提交的更新字段。

    Returns:
        tuple: ``(User, None)`` 成功；``(None, (error_msg, status_code))`` 失败。
    """
    from apps.system.utils.dept_scope import get_dept_subtree

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return (None, ("未找到用户", 404))

    if not request.user.is_superuser:
        _req_p = getattr(request.user, "profile", None)
        _req_level = _req_p.admin_level if _req_p else AdminLevel.MEMBER
        if _req_level == AdminLevel.DEPT_ADMIN and _req_p and _req_p.dept_id:
            _target_p = getattr(user, "profile", None)
            _target_dept = getattr(_target_p, "dept_id", None)
            if _target_dept is None or _target_dept not in get_dept_subtree(_req_p.dept_id):
                return (None, ("无权编辑其他部门的用户", 403))

    _old_email = user.email
    _old_is_active = user.is_active

    user.email = payload.get("email", user.email)
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
            if user.username == "admin":
                pass
            else:
                pid = payload.get("positionId")
                if pid:
                    try:
                        pos = Position.objects.get(pk=pid)
                        if pos.is_builtin:
                            return (None, ("内置岗位不可手动分配给用户", 400))
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
                    if not request.user.is_superuser:
                        try:
                            _req_profile = getattr(request.user, "profile", None)
                            _req_level = _req_profile.admin_level if _req_profile else AdminLevel.MEMBER
                        except Exception:
                            _req_level = AdminLevel.MEMBER
                        if lvl < _req_level:
                            return (None, ("无权设置高于自身权限的管理级别", 403))
                    profile.admin_level = lvl
            except (ValueError, TypeError):
                pass

        profile.save()

        if "extraGroupIds" in payload:
            extra_ids = payload.get("extraGroupIds") or []
            if isinstance(extra_ids, str):
                extra_ids = [s.strip() for s in extra_ids.split(",") if s.strip()]
            try:
                profile.extra_nc_groups.set(extra_ids)
            except Exception as exc:
                logger.warning("[UserWriteService][update] 设置 extra_nc_groups 失败: %s", exc)

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

    logger.info("[UserWriteService][update] user_id=%s", user_id)
    return (user, None)


def delete_users(request, ids: list[str]):
    """批量删除用户，同步 NC 群组移除。

    Args:
        request: DRF request 对象（用于权限校验）。
        ids (list[str]): 待删除用户 ID 列表。

    Returns:
        tuple: ``(None, None)`` 成功；``(None, (error_msg, status_code))`` 失败。
    """
    from apps.system.utils.dept_scope import get_dept_subtree

    users_qs = User.objects.filter(id__in=ids)
    if not users_qs.exists():
        return (None, ("未找到用户", 404))

    if not request.user.is_superuser:
        _req_p = getattr(request.user, "profile", None)
        _req_level = _req_p.admin_level if _req_p else AdminLevel.MEMBER
        if _req_level == AdminLevel.DEPT_ADMIN and _req_p and _req_p.dept_id:
            _allowed = get_dept_subtree(_req_p.dept_id)
            for u in users_qs:
                u_profile = getattr(u, "profile", None)
                u_dept = getattr(u_profile, "dept_id", None)
                if u_dept is None or u_dept not in _allowed:
                    return (None, ("无权删除其他部门的用户", 403))

    for user in users_qs:
        profile = getattr(user, "profile", None)
        if profile:
            try:
                NcSyncService.on_user_deleted(profile)
            except Exception as exc:
                logger.warning("[UserWriteService][delete] NC 同步入队失败: %s", exc)

    users_qs.delete()
    return (None, None)


def reset_user_password(user_id: str, password: str = "123456"):
    """重置用户密码。

    Args:
        user_id (str): 用户 ID。
        password (str): 新密码，默认 "123456"。

    Returns:
        tuple: ``(None, None)`` 成功；``(None, (error_msg, status_code))`` 失败。
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return (None, ("未找到用户", 404))

    user.set_password(password)
    user.save()
    logger.info("[UserWriteService][reset_password] user_id=%s", user_id)
    return (None, None)


def change_user_password(request, payload: dict):
    """用户自行修改密码（需提供旧密码验证）。

    Args:
        request: DRF request 对象。
        payload (dict): 包含 oldPassword 和 password 字段。

    Returns:
        tuple: ``(None, None)`` 成功；``(None, (error_msg, status_code))`` 失败。
    """
    old_pwd = payload.get("oldPassword")
    new_pwd = payload.get("password")

    if not old_pwd or not new_pwd:
        return (None, ("原密码和新密码不能为空", 400))

    user = request.user
    if not user.is_authenticated:
        return (None, ("未认证", 401))

    if not user.check_password(old_pwd):
        return (None, ("原密码错误", 400))

    if len(new_pwd) < 6:
        return (None, ("新密码长度不能少于6位", 400))

    user.set_password(new_pwd)
    user.save()
    logger.info("[UserWriteService][change_password] user=%s", user.username)
    return (None, None)
