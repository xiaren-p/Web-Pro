"""用户相关视图。

模块说明：提供用户查询、创建、更新、删除、导入导出、密码重置与 Seafile 同步等接口。
"""

import os
import re
import uuid
import json
import csv
import io
import time
import requests
from urllib.parse import quote
from datetime import datetime, timedelta

from django.db.models import Q
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.models import (
    Role, Department, DictItem, UserProfile
)
from api_v1.serializers import (
    UserSerializer, MobileCodeSendSerializer, MobileBindSerializer, 
    EmailCodeSendSerializer, EmailBindSerializer
)
from api_v1.utils.responses import drf_ok, drf_error
from api_v1.utils.pagination import paginate_queryset
# write_log 调用已移除

class UserViewSet(viewsets.ViewSet):
    """用户相关接口

    路由前缀：/users
    支持：分页、详情、创建、更新、删除、导入导出、密码修改/重置、个人资料、下拉选项
    """

    @csrf_exempt
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        t0 = time.perf_counter()
        user = request.user
        if not user.is_authenticated:
            return drf_error("未登录", status=401)
        profile = getattr(user, "profile", None)
        roles = list(profile.roles.values_list("code", flat=True)) if profile else []
        # 若为 Django 超级用户或拥有 admin 角色，追加 ROOT 角色，前端将视为超级管理员
        try:
            is_admin_role = profile.roles.filter(code='admin').exists() if profile else False
        except Exception:
            is_admin_role = False
        if user.is_superuser or is_admin_role:
            if "ROOT" not in roles:
                roles.append("ROOT")

        # 聚合基于角色的菜单权限点（供前端按钮级权限使用）
        perms_set = set()
        try:
            if profile:
                role_ids = list(profile.roles.values_list('id', flat=True))
                if role_ids:
                    from api_v1.models import Menu
                    for p in Menu.objects.filter(status=True, roles__in=role_ids).exclude(perms="").values_list("perms", flat=True).distinct():
                        # 支持以逗号/空格分隔的多权限配置
                        for token in str(p).replace('\n', ' ').replace('\t', ' ').split(','):
                            token = token.strip()
                            if token:
                                perms_set.add(token)
        except Exception:
            pass

        perms = sorted(perms_set)
        # 将头像转换为绝对 URL（避免前端在不同端口下 /media 相对路径无法加载）
        def abs_avatar(v: str) -> str:
            try:
                if not v:
                    # 若未配置用户头像，回退到 settings 中的 DEFAULT_AVATAR_URL（若有）
                    default_avatar = getattr(settings, 'DEFAULT_AVATAR_URL', '') or ''
                    return default_avatar
                if str(v).startswith("http://") or str(v).startswith("https://"):
                    return v
                # 统一补齐到 MEDIA_URL
                base = settings.MEDIA_URL.rstrip('/')
                p = str(v)
                if p.startswith('/media/'):
                    rel = p
                elif p.startswith('media/'):
                    rel = '/' + p
                elif p.startswith('uploads/'):
                    rel = base + '/' + p
                else:
                    rel = p if p.startswith('/') else ('/' + p)
                # 如果设置了对外可访问的后端 URL（BACKEND_EXTERNAL_URL），优先使用该值构建外部可访问链接
                external = getattr(settings, 'BACKEND_EXTERNAL_URL', '') or ''
                external = external.rstrip('/')
                if external:
                    return external + rel
                # 否则使用 request 的 Host 构建绝对 URI（兼容本地/代理调试）
                return request.build_absolute_uri(rel)
            except Exception:
                return v or ""

        resp = drf_ok({
            "userId": user.id,
            "username": user.username,
            "nickname": profile.nickname if profile else "",
            "avatar": abs_avatar(profile.avatar if profile else ""),
            "roles": roles,
            "perms": perms,
        })
        # logging removed
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

        # 数据权限过滤：基于当前登录用户的所有角色 data_scope 计算可访问用户集合
        # 优先：超级用户 或 拥有 admin 角色 -> 不限制
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            if not user.is_superuser:
                profile = getattr(user, 'profile', None)
                is_admin_role = False
                try:
                    if profile:
                        is_admin_role = profile.roles.filter(code='admin').exists()
                except Exception:
                    is_admin_role = False
                if not is_admin_role and profile:
                    # 汇总所有角色的 data_scope，采用“并集”策略：若任一角色拥有更广泛范围则扩大可见性
                    scopes = list(profile.roles.values_list('data_scope', flat=True)) or []
                    # 默认无角色则最小范围=本人
                    scopes = scopes or [4]
                    # 若包含 1 (全部数据) 直接跳过限制
                    if 1 not in scopes:
                        # 预取当前用户所属部门及所有子部门
                        dept_ids_union = set()
                        if profile.dept_id:
                            def collect(did):
                                if did in dept_ids_union:
                                    return
                                dept_ids_union.add(did)
                                for cid in Department.objects.filter(parent_id=did).values_list('id', flat=True):
                                    collect(cid)
                            collect(profile.dept_id)
                        # 构造 Q 条件并集
                        perm_q = Q(pk__in=[user.id])  # 本人
                        # 若存在 3 (本部门)，允许同部门用户
                        if 3 in scopes and profile.dept_id:
                            perm_q |= Q(profile__dept_id=profile.dept_id)
                        # 若存在 2 (部门及子部门)，允许当前部门及其子孙
                        if 2 in scopes and dept_ids_union:
                            perm_q |= Q(profile__dept_id__in=list(dept_ids_union))
                        # 将过滤应用（若仅本人则 perm_q 只是本人）
                        qs = qs.filter(perm_q)
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
        t0 = time.perf_counter()
        payload = request.data.copy()
        username = payload.get("username")
        password = payload.get("password") or "123456"
        email = payload.get("email") or ""
        nickname = payload.get("nickname") or ""
        mobile = payload.get("mobile") or ""
        # 若未显式传入 avatar，使用 settings.DEFAULT_AVATAR_URL
        avatar = payload.get("avatar") or getattr(settings, 'DEFAULT_AVATAR_URL', '') or ""
        dept_id = payload.get("deptId")
        role_ids = payload.get("roleIds") or []
        status_num = payload.get("status", 1)
        gender = payload.get("gender")
        if not username:
            return drf_error("用户名不能为空", status=400)
        if User.objects.filter(username=username).exists():
            return drf_error("用户名已存在", status=400)
        user = User.objects.create(username=username, email=email, is_active=bool(int(status_num)))
        user.set_password(password)
        user.save()
        profile = UserProfile.objects.create(user=user, nickname=nickname, mobile=mobile, avatar=avatar, dept_id=dept_id, cloud_id=payload.get("cloudId", "") or "")
        if gender is not None:
            try:
                profile.gender = int(gender)
            except Exception:
                pass
        if role_ids:
            profile.roles.set(Role.objects.filter(id__in=role_ids))
        profile.save()
        # logging removed
        return drf_ok(UserSerializer(user).data, status=201)

    @action(detail=False, methods=["put"], url_path=r"(?P<id>[^/]+)")
    def update(self, request, id: str):
        t0 = time.perf_counter()
        try:
            user = User.objects.get(pk=id)
        except User.DoesNotExist:
            return drf_error("未找到用户", status=404)
        payload = request.data.copy()
        user.email = payload.get("email", user.email)
        user.is_active = bool(int(payload.get("status", 1)))
        user.save()
        profile = getattr(user, "profile", None)
        seafile_sync = None
        if profile:
            profile.nickname = payload.get("nickname", profile.nickname)
            profile.mobile = payload.get("mobile", profile.mobile)
            profile.avatar = payload.get("avatar", profile.avatar)
            profile.dept_id = payload.get("deptId", profile.dept_id)
            # 支持通过 API 写入 cloudId（用于手动回填 Seafile 的 cloud identifier）
            if "cloudId" in payload:
                try:
                    profile.cloud_id = payload.get("cloudId") or ""
                except Exception:
                    pass
            if payload.get("gender") is not None:
                try:
                    profile.gender = int(payload.get("gender"))
                except Exception:
                    pass
            role_ids = payload.get("roleIds") or []
            if role_ids:
                profile.roles.set(Role.objects.filter(id__in=role_ids))
            profile.save()
            # 如果配置了 profile.cloud_id，尝试同步更新 Seafile 管理端的信息
            try:
                cloud_id_val = (profile.cloud_id or "").strip()
            except Exception:
                cloud_id_val = ""
            if cloud_id_val:
                seafile_sync = None
                # 读取 Seafile 管理凭据（与 cloud_create/delete 逻辑一致）
                s_site = s_user = s_pass = None
                try:
                    items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
                    if items:
                        for it in items:
                            label = (it.label or "").lower()
                            val = (it.value or "").strip()
                            if not s_site and ("site" in label or "站" in label or val.startswith("http")):
                                s_site = val
                                continue
                            if not s_user and ("admin" in label or "管理员" in label or "username" in label):
                                s_user = val
                                continue
                            if not s_pass and ("pass" in label or "密码" in label or "pwd" in label):
                                s_pass = val
                                continue
                        if (not s_site or not s_user or not s_pass) and items[0] and items[0].value:
                            try:
                                j = json.loads(items[0].value)
                                s_site = s_site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                                s_user = s_user or j.get("username") or j.get("user") or j.get("admin")
                                s_pass = s_pass or j.get("password") or j.get("pass") or j.get("pwd")
                            except Exception:
                                pass
                except Exception:
                    items = []

                if s_site and s_user and s_pass:
                    base_site = str(s_site).strip()
                    if not re.match(r"^https?://", base_site, re.I):
                        base_site = "https://" + base_site
                    auth_url = base_site.rstrip("/")
                    if not re.search(r"api2/auth-token", auth_url, re.I):
                        auth_url = auth_url + "/api2/auth-token/"

                    token = None
                    try:
                        resp = requests.post(auth_url, json={"username": s_user, "password": s_pass}, timeout=10)
                        if 200 <= resp.status_code < 300:
                            try:
                                token = resp.json().get("token")
                            except Exception:
                                token = None
                    except Exception as e:
                        token = None

                    if token:
                        headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
                        admin_put_url = base_site.rstrip("/") + f"/api/v2.1/admin/users/{quote(cloud_id_val)}/"
                        admin_result = {"success": None, "msg": "skipped"}
                        account_result = {"success": None, "msg": "skipped"}
                        try:
                            # 尝试调用
                            r = requests.put(admin_put_url, data={"name": profile.nickname or "", "contact_email": user.email or ""}, headers=headers, timeout=10)
                            if 200 <= r.status_code < 300:
                                admin_result = {"success": True, "msg": f"{r.status_code}"}
                            else:
                                admin_result = {"success": False, "msg": f"{r.status_code} {getattr(r, 'text', '')}"}
                        except Exception as e:
                            admin_result = {"success": False, "msg": f"请求失败: {e}"}

                        # 同时向 /api2/accounts/{cloudID}/ 发送 PUT 更新账号状态（is_active）
                        try:
                            account_url = base_site.rstrip("/") + f"/api2/accounts/{quote(cloud_id_val)}/"
                            acct_headers = {"Authorization": f"Token {token}", "Content-Type": "application/x-www-form-urlencoded"}
                            is_active_val = "true" if getattr(user, 'is_active', True) else "false"
                            try:
                                ar = requests.put(account_url, data={"is_active": is_active_val}, headers=acct_headers, timeout=10)
                                if 200 <= ar.status_code < 300:
                                    account_result = {"success": True, "msg": f"{ar.status_code}"}
                                else:
                                    account_result = {"success": False, "msg": f"{ar.status_code} {getattr(ar, 'text', '')}"}
                            except Exception as e:
                                account_result = {"success": False, "msg": f"请求失败: {e}"}
                        except Exception:
                            account_result = {"success": False, "msg": "构建 account_url 失败"}

                        # 构造兼容的 seafile_sync：保留 top-level success，并带上详细项
                        overall = bool(admin_result.get("success") and account_result.get("success"))
                        seafile_sync = {
                            "success": overall,
                            "msg": "",
                            "adminPut": admin_result,
                            "accountPut": account_result,
                        }
                        if not overall:
                            # 用简短信息填充 msg 便于前端展示
                            msgs = []
                            if admin_result.get("success") is False:
                                msgs.append(f"admin:{admin_result.get('msg')}")
                            if account_result.get("success") is False:
                                msgs.append(f"account:{account_result.get('msg')}")
                            seafile_sync["msg"] = "; ".join(msgs) if msgs else seafile_sync.get("msg", "")
                    else:
                        seafile_sync = {"success": False, "msg": "未能获取 Seafile token"}
                else:
                    seafile_sync = {"success": False, "msg": "未配置完整的 Seafile 管理凭据"}
                # seafile sync logging removed
        resp_data = UserSerializer(user).data
        # 若有 Seafile 同步结果，将其加入返回数据，便于前端显示
        if seafile_sync is not None:
            resp_data['seafileSync'] = seafile_sync
        return drf_ok(resp_data)

    @action(detail=False, methods=["delete"], url_path=r"(?P<id>[^/]+)")
    def delete(self, request, id: str):
        t0 = time.perf_counter()
        # 支持单个或逗号分隔的批量删除，并在删除时同步调用 Seafile 的删除接口
        try:
            # 解析 ids 列表
            if isinstance(id, str) and "," in id:
                ids = [s.strip() for s in id.split(",") if s.strip()]
            else:
                ids = [id]

            # 获取待删除用户对象列表
            users_qs = User.objects.filter(id__in=ids)
            if not users_qs.exists():
                return drf_error("未找到用户", status=404)

            users = list(users_qs)

            cloud_results = []
            # 仅使用 profile.cloud_id 作为远端删除标识；若 profile.cloud_id 未配置，则跳过远端删除并记录
            # 从字典读取 Seafile 配置（复用 cloud_create 的解析逻辑）
            site = admin_user = admin_pass = None
            try:
                items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
                if items:
                    for it in items:
                        label = (it.label or "").lower()
                        val = (it.value or "").strip()
                        if not site and ("site" in label or "站" in label or val.startswith("http")):
                            site = val
                            continue
                        if not admin_user and ("admin" in label or "管理员" in label or "username" in label):
                            admin_user = val
                            continue
                        if not admin_pass and ("pass" in label or "密码" in label or "pwd" in label):
                            admin_pass = val
                            continue
                    if (not site or not admin_user or not admin_pass) and items[0] and items[0].value:
                        try:
                            j = json.loads(items[0].value)
                            site = site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                            admin_user = admin_user or j.get("username") or j.get("user") or j.get("admin")
                            admin_pass = admin_pass or j.get("password") or j.get("pass") or j.get("pwd")
                        except Exception:
                            pass
            except Exception:
                items = []

            # 收集需要在 Seafile 上删除的目标（依据 profile.cloud_id）
            cloud_targets = []
            for u in users:
                profile = getattr(u, 'profile', None)
                try:
                    cloud_id_val = (profile.cloud_id or "").strip() if profile else ""
                except Exception:
                    cloud_id_val = ""
                if cloud_id_val:
                    cloud_targets.append((u, cloud_id_val))
                else:
                    cloud_results.append({"id": u.id, "email": (u.email or ""), "success": False, "msg": "未配置 cloud_id，跳过远端删除"})

            # 若存在需要远程删除的目标且有完整 Seafile 管理凭据，则调用批量删除接口
            if cloud_targets and site and admin_user and admin_pass:
                base_site = str(site).strip()
                if not re.match(r"^https?://", base_site, re.I):
                    base_site = "https://" + base_site
                auth_url = base_site.rstrip("/")
                if not re.search(r"api2/auth-token", auth_url, re.I):
                    auth_url = auth_url + "/api2/auth-token/"

                token = None
                try:
                    resp = requests.post(auth_url, json={"username": admin_user, "password": admin_pass}, timeout=10)
                    if 200 <= resp.status_code < 300:
                        try:
                            token = resp.json().get("token")
                        except Exception:
                            token = None
                except Exception as e:
                    pass  # seafile token fetch failed (logging removed)

                if token:
                    headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
                    batch_url = base_site.rstrip("/") + "/api/v2.1/admin/users/batch/"
                    for (u, target_email) in cloud_targets:
                        payload = {"email": target_email, "operation": "delete-user"}
                        try:
                            r = requests.post(batch_url, data=payload, headers=headers, timeout=10)
                            if 200 <= r.status_code < 300:
                                cloud_results.append({"id": u.id, "email": target_email, "success": True, "msg": f"{r.status_code}"})
                            else:
                                txt = getattr(r, 'text', '')
                                cloud_results.append({"id": u.id, "email": target_email, "success": False, "msg": f"{r.status_code} {txt}"})
                        except Exception as e:
                            cloud_results.append({"id": u.id, "email": target_email, "success": False, "msg": f"请求失败: {e}"})
                else:
                    pass  # seafile token missing (logging removed)
            else:
                if cloud_targets and not (site and admin_user and admin_pass):
                    pass  # missing seafile credentials (logging removed)

            # 执行本地删除
            count = users_qs.count()
            users_qs.delete()
            # 记录日志（包含远端删除汇总信息）
            succ = sum(1 for r in cloud_results if r.get('success'))
            failc = sum(1 for r in cloud_results if not r.get('success'))
            # logging removed
            # 返回本地删除与云端删除的详细结果，前端将据此展示提示
            return drf_ok({
                "deletedCount": count,
                "cloudResults": cloud_results,
                "successCount": succ,
                "failCount": failc,
            })
        except User.DoesNotExist:
            return drf_error("未找到用户", status=404)
        except Exception as e:
            return drf_error("服务器内部错误", status=500)

    @action(detail=False, methods=["put"], url_path=r"(?P<id>[^/]+)/password/reset")
    def reset_password(self, request, id: str):
        t0 = time.perf_counter()
        try:
            user = User.objects.get(pk=id)
        except User.DoesNotExist:
            # write_log removed: 重置密码失败：未找到用户（ID={id}）
            return drf_error("未找到用户", status=404)
        password = request.query_params.get("password") or "123456"
        user.set_password(password)
        user.save()
        # 尝试同步修改 Seafile 账号密码（若存在 profile.cloud_id）并把结果返回给前端
        seafile_sync = None
        try:
            profile = getattr(user, 'profile', None)
            cloud_id_val = (profile.cloud_id or "").strip() if profile else ""
        except Exception:
            cloud_id_val = ""

        if cloud_id_val:
            # 读取 Seafile 管理凭据
            s_site = s_user = s_pass = None
            try:
                items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
                if items:
                    for it in items:
                        label = (it.label or "").lower()
                        val = (it.value or "").strip()
                        if not s_site and ("site" in label or "站" in label or val.startswith("http")):
                            s_site = val
                            continue
                        if not s_user and ("admin" in label or "管理员" in label or "username" in label):
                            s_user = val
                            continue
                        if not s_pass and ("pass" in label or "密码" in label or "pwd" in label):
                            s_pass = val
                            continue
                    if (not s_site or not s_user or not s_pass) and items[0] and items[0].value:
                        try:
                            j = json.loads(items[0].value)
                            s_site = s_site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                            s_user = s_user or j.get("username") or j.get("user") or j.get("admin")
                            s_pass = s_pass or j.get("password") or j.get("pass") or j.get("pwd")
                        except Exception:
                            pass
            except Exception:
                items = []

            if s_site and s_user and s_pass:
                base_site = str(s_site).strip()
                if not re.match(r"^https?://", base_site, re.I):
                    base_site = "https://" + base_site
                auth_url = base_site.rstrip("/")
                if not re.search(r"api2/auth-token", auth_url, re.I):
                    auth_url = auth_url + "/api2/auth-token/"

                token = None
                try:
                    resp = requests.post(auth_url, json={"username": s_user, "password": s_pass}, timeout=10)
                    if 200 <= resp.status_code < 300:
                        try:
                            token = resp.json().get("token")
                        except Exception:
                            token = None
                except Exception:
                    token = None

                if token:
                    acct_headers = {"Authorization": f"Token {token}", "Content-Type": "application/x-www-form-urlencoded"}
                    account_url = base_site.rstrip("/") + f"/api2/accounts/{quote(cloud_id_val)}/"
                    try:
                        ar = requests.put(account_url, data={"password": password}, headers=acct_headers, timeout=10)
                        if 200 <= ar.status_code < 300:
                            seafile_sync = {"success": True, "msg": f"{ar.status_code}", "accountPut": {"success": True, "msg": f"{ar.status_code}"}}
                        else:
                            seafile_sync = {"success": False, "msg": f"{ar.status_code} {getattr(ar, 'text', '')}", "accountPut": {"success": False, "msg": f"{ar.status_code} {getattr(ar, 'text', '')}"}}
                    except Exception as e:
                        seafile_sync = {"success": False, "msg": f"请求失败: {e}", "accountPut": {"success": False, "msg": f"请求失败: {e}"}}
                else:
                    seafile_sync = {"success": False, "msg": "未能获取 Seafile token", "accountPut": {"success": False, "msg": "未能获取 Seafile token"}}
            else:
                seafile_sync = {"success": False, "msg": "未配置完整的 Seafile 管理凭据", "accountPut": {"success": False, "msg": "未配置完整的 Seafile 管理凭据"}}

        # 记录日志（已移除）: 重置用户密码（ID={id}）

        resp = {"message": "password reset"}
        if seafile_sync is not None:
            resp['seafileSync'] = seafile_sync
        return drf_ok(resp)

    @action(detail=False, methods=["get"], url_path="template")
    def template(self, request):
        t0 = time.perf_counter()
        # 返回一个简单的 CSV 模板
        content = "username,email,nickname,mobile,deptId,roleIds\n"
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=users_template.csv"
        # write_log removed: 下载用户导入模板
        return response

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        t0 = time.perf_counter()
        # 导出所有用户为 CSV
        users = User.objects.all().order_by("id")
        content = "username,email,nickname,mobile,deptId,roleIds\n"
        for u in users:
            profile = getattr(u, "profile", None)
            role_ids = ",".join(str(r.id) for r in profile.roles.all()) if profile else ""
            dept_id = profile.dept_id if profile else ""
            content += f"{u.username},{u.email},{profile.nickname if profile else ''},{profile.mobile if profile else ''},{dept_id},{role_ids}\n"
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=users_export.csv"
        try:
            cnt = users.count()
        except Exception:
            cnt = 0
        # write_log removed: 导出用户列表：{cnt} 条
        return response

    @action(detail=False, methods=["post"], url_path="import")
    def import_users(self, request):
        t0 = time.perf_counter()
        # 支持 CSV 文件导入
        file = request.FILES.get("file")
        if not file:
            return drf_error("未上传文件", status=400)
        reader = csv.DictReader(io.StringIO(file.read().decode()))
        count = 0
        default_avatar = getattr(settings, 'DEFAULT_AVATAR_URL', '')
        for row in reader:
            username = row.get("username")
            if not username or User.objects.filter(username=username).exists():
                continue
            user = User.objects.create(username=username, email=row.get("email", ""), is_active=True)
            user.set_password("123456")
            user.save()
            # 导入时若无头像，使用默认头像
            avatar = row.get("avatar") or default_avatar
            profile = UserProfile.objects.create(user=user, nickname=row.get("nickname", ""), mobile=row.get("mobile", ""), dept_id=row.get("deptId"), avatar=avatar)
            role_ids = row.get("roleIds", "").split(",") if row.get("roleIds") else []
            if role_ids:
                profile.roles.set(Role.objects.filter(id__in=role_ids))
            profile.save()
            count += 1
        # logging removed
        return drf_ok({"success": True, "count": count})

    @action(detail=False, methods=["post"], url_path="cloud-create", permission_classes=[IsAuthenticated])
    def cloud_create(self, request):
        """后端代理：为选中用户在 Seafile 上创建账号。

        请求 JSON:
        { "ids": [1,2,3], "passwords": {"1": "pwd1", "2": "pwd2"} }

        返回:
        { results: [{id, email, username, success, msg}], successCount, failCount }
        """
        data = request.data or {}
        ids = data.get("ids") or data.get("userIds") or []
        if isinstance(ids, str):
            ids = [x.strip() for x in ids.split(",") if x.strip()]
        passwords = data.get("passwords") or {}

        # 读取字典 cloud_type / clooud_type
        site = admin_user = admin_pass = None
        try:
            items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
            if items:
                for it in items:
                    label = (it.label or "").lower()
                    val = (it.value or "").strip()
                    if not site and ("site" in label or "站" in label or val.startswith("http")):
                        site = val
                        continue
                    if not admin_user and ("admin" in label or "管理员" in label or "username" in label):
                        admin_user = val
                        continue
                    if not admin_pass and ("pass" in label or "密码" in label or "pwd" in label):
                        admin_pass = val
                        continue
                # 若仍不完整，尝试解析首项为 JSON
                if (not site or not admin_user or not admin_pass) and items[0] and items[0].value:
                    try:
                        j = json.loads(items[0].value)
                        site = site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                        admin_user = admin_user or j.get("username") or j.get("user") or j.get("admin")
                        admin_pass = admin_pass or j.get("password") or j.get("pass") or j.get("pwd")
                    except Exception:
                        pass
        except Exception:
            items = []

        if not site or not admin_user or not admin_pass:
            return drf_error("未在字典中找到完整的 Seafile 站点和管理员凭据，请在字典 cloud_type 中配置 site/admin/password", status=400)

        base_site = str(site).strip()
        if not re.match(r"^https?://", base_site, re.I):
            base_site = "https://" + base_site
        auth_url = base_site.rstrip("/")
        if not re.search(r"api2/auth-token", auth_url, re.I):
            auth_url = auth_url + "/api2/auth-token/"

        try:
            resp = requests.post(auth_url, json={"username": admin_user, "password": admin_pass}, timeout=10)
        except Exception as e:
            # write_log removed: 创建 cloud 用户失败: 获取 token 错误
            return drf_error(f"请求 Seafile 获取 token 失败: {e}", status=502)

        if resp.status_code < 200 or resp.status_code >= 300:
            try:
                txt = resp.text
            except Exception:
                txt = ""
            # write_log removed: 创建 cloud 用户失败: Seafile 返回 {resp.status_code}
            return drf_error(f"Seafile 返回错误: {resp.status_code} {txt}", status=502)

        try:
            token = resp.json().get("token")
        except Exception:
            token = None
        if not token:
            return drf_error("未从 Seafile 获取到 token，请检查字典中管理员账号/密码是否正确", status=502)

        results = []
        success = 0
        fail = 0
        headers = {"Authorization": f"Token {token}", "Content-Type": "application/x-www-form-urlencoded"}
        for uid in ids:
            try:
                u = User.objects.get(pk=uid)
            except Exception:
                results.append({"id": uid, "success": False, "msg": "未找到用户"})
                fail += 1
                continue
            email = (u.email or "").strip()
            if not email:
                results.append({"id": uid, "username": u.username, "success": False, "msg": "未配置邮箱"})
                fail += 1
                continue
            pwd = None
            # 密码可能按 id 字符串或数字 key 存在
            if str(uid) in passwords:
                pwd = passwords.get(str(uid))
            elif isinstance(uid, int) and uid in passwords:
                pwd = passwords.get(uid)  # type: ignore
            if not pwd:
                results.append({"id": uid, "email": email, "username": u.username, "success": False, "msg": "未提供密码"})
                fail += 1
                continue

            account_url = base_site.rstrip("/") + f"/api2/accounts/{quote(email)}/"
            form = {
                "password": pwd,
                "is_staff": "false",
                "is_active": ("true" if getattr(u, 'is_active', True) else "false"),
                "name": (u.profile.nickname if getattr(u, 'profile', None) else u.username),
            }
            try:
                r = requests.put(account_url, data=form, headers=headers, timeout=10)
            except Exception as e:
                results.append({"id": uid, "email": email, "username": u.username, "success": False, "msg": f"请求创建失败: {e}"})
                fail += 1
                continue
            if 200 <= r.status_code < 300:
                # 解析返回 JSON，尝试读取 Seafile 返回的 email 作为 cloud_id 并保存到 profile
                returned_email = None
                try:
                    jr = r.json()
                    returned_email = jr.get("email") if isinstance(jr, dict) else None
                except Exception:
                    returned_email = None
                try:
                    profile = getattr(u, 'profile', None)
                    if profile and returned_email:
                        profile.cloud_id = returned_email
                        profile.save()
                except Exception:
                    pass
                # 若成功创建并获得 returned_email，则向 admin users 接口绑定 login_id
                admin_bind = {"success": None, "msg": "skipped"}
                if returned_email:
                    try:
                        admin_put_url = base_site.rstrip("/") + f"/api/v2.1/admin/users/{quote(returned_email)}/"
                        try:
                            # 以 form-data 方式提交 login_id
                            ap = requests.put(admin_put_url, data={"login_id": u.username}, headers=headers, timeout=10)
                            if 200 <= ap.status_code < 300:
                                admin_bind = {"success": True, "msg": f"{ap.status_code}"}
                            else:
                                admin_bind = {"success": False, "msg": f"{ap.status_code} {getattr(ap, 'text', '')}"}
                        except Exception as e:
                            admin_bind = {"success": False, "msg": f"请求失败: {e}"}
                    except Exception:
                        admin_bind = {"success": False, "msg": "构建 admin_put_url 失败"}

                results.append({"id": uid, "email": email, "username": u.username, "cloudId": returned_email, "success": True, "msg": "created", "adminBind": admin_bind})
                success += 1
            else:
                txt = r.text if hasattr(r, 'text') else ''
                results.append({"id": uid, "email": email, "username": u.username, "success": False, "msg": f"{r.status_code} {txt}"})
                fail += 1

        # write_log removed: 批量创建 cloud 用户：成功 {success}，失败 {fail}
        return drf_ok({"results": results, "successCount": success, "failCount": fail})

    @action(detail=False, methods=["get"], url_path="profile")
    def profile_get(self, request):
        user = request.user
        if not user.is_authenticated:
            return drf_error("未登录", status=401)
        # 补充前端常用聚合字段（与 /users/me 保持一致但包含更详细的角色/部门信息）
        profile = getattr(user, 'profile', None)
        dept_name = ''
        role_names = ''
        if profile:
            if profile.dept:
                dept_name = profile.dept.name
            try:
                role_names = ','.join(profile.roles.values_list('name', flat=True))
            except Exception:
                role_names = ''
        data = UserSerializer(user).data
        # 补充 seafileCached 布尔，便于前端判断是否需要提示 cloud 密码
        try:
            site = None
            try:
                items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
                if items:
                    for it in items:
                        label = (it.label or "").lower()
                        val = (it.value or "").strip()
                        if not site and ("site" in label or "站" in label or val.startswith("http")):
                            site = val
                            break
                    if (not site) and items[0] and items[0].value:
                        try:
                            j = json.loads(items[0].value)
                            site = site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                        except Exception:
                            pass
            except Exception:
                site = None

            if site:
                base_site = str(site).strip()
                if not re.match(r"^https?://", base_site, re.I):
                    base_site = "https://" + base_site
                try:
                    from api_v1.utils.seafile import get_cached_token
                    cached = bool(get_cached_token(user, base_site))
                    data['seafileCached'] = cached
                except Exception:
                    data['seafileCached'] = False
            else:
                data['seafileCached'] = False
        except Exception:
            data['seafileCached'] = False
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
        data['deptName'] = dept_name or data.get('deptName', '')
        data['roleNames'] = role_names or data.get('roleNames', '')
        # write_log removed: 查看个人资料
        return drf_ok(data)

    @action(detail=False, methods=["put"], url_path="profile")
    def profile_put(self, request):
        t0 = time.perf_counter()
        user = request.user
        if not user.is_authenticated:
            return drf_error("未登录", status=401)
        payload = request.data.copy()
        profile = getattr(user, "profile", None)
        seafile_profile_sync = None
        seafile_cached_flag = None
        if profile:
            profile.nickname = payload.get("nickname", profile.nickname)
            profile.mobile = payload.get("mobile", profile.mobile)
            profile.avatar = payload.get("avatar", profile.avatar)
            profile.dept_id = payload.get("deptId", profile.dept_id)
            role_ids = payload.get("roleIds") or []
            if role_ids:
                profile.roles.set(Role.objects.filter(id__in=role_ids))
            profile.save()
            # 尝试使用当前用户凭据同步 Seafile 昵称（必须使用当前账户登录）
            try:
                req_password = (request.data or {}).get('cloudPassword') or (request.data or {}).get('password') or None
            except Exception:
                req_password = None

            try:
                # 读取字典以获取 Seafile 站点地址（site），但不使用字典中的用户名/密码作为登录凭据
                site = None
                items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
                if items:
                    for it in items:
                        label = (it.label or "").lower()
                        val = (it.value or "").strip()
                        if not site and ("site" in label or "站" in label or val.startswith("http")):
                            site = val
                            continue
                    if (not site) and items[0] and items[0].value:
                        try:
                            j = json.loads(items[0].value)
                            site = site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                        except Exception:
                            pass
            except Exception:
                site = None

            if site:
                # 优先尝试使用已缓存的 CloudAuthToken；若不存在或过期，尝试使用前端提供的当前用户密码获取并缓存
                try:
                    base_site = str(site).strip()
                    if not re.match(r"^https?://", base_site, re.I):
                        base_site = "https://" + base_site
                    auth_url = base_site.rstrip("/")
                    if not re.search(r"api2/auth-token", auth_url, re.I):
                        auth_url = auth_url + "/api2/auth-token/"

                    # 优先检查缓存的 token：若存在则直接使用；否则按需要求前端提供当前用户密码以获取并缓存 token
                    try:
                        from api_v1.utils.seafile import get_cached_token, get_or_fetch_user_token, sync_profile_name, invalidate_user_token
                        cached = get_cached_token(user, base_site)
                        if cached:
                            r = sync_profile_name(base_site, cached, profile.nickname)
                            if r is None:
                                seafile_profile_sync = {"success": False, "msg": "请求失败: Seafile 请求异常"}
                            else:
                                if 200 <= r.status_code < 300:
                                    seafile_profile_sync = {"success": True, "msg": f"{r.status_code}"}
                                else:
                                    if r.status_code in (401, 403):
                                        try:
                                            invalidate_user_token(user, base_site)
                                        except Exception:
                                            pass
                                        seafile_profile_sync = {"success": False, "msg": f"Seafile 认证失败({r.status_code})，已失效缓存，请重新登录以刷新 token"}
                                    else:
                                        seafile_profile_sync = {"success": False, "msg": f"{r.status_code} {getattr(r, 'text', '')}"}
                        else:
                            # cache miss: require frontend to provide current user's password
                            if not req_password:
                                seafile_profile_sync = {"success": False, "msg": "未提供当前用户密码，需提供以完成 Seafile 同步"}
                            else:
                                # 验证当前密码与 Django 存储的密码一致；若不一致则不尝试用管理员凭据回退
                                try:
                                        # 尝试使用前端提供的密码向 Seafile 获取 token（不强制其必须与系统密码一致）
                                        token, err = get_or_fetch_user_token(user, base_site, provided_password=req_password, request=request)
                                        if token:
                                            # 成功从 Seafile 获取 token 后，缓存到后端（便于后续免密访问）
                                            try:
                                                from api_v1.utils.seafile import cache_token_for_user
                                                cache_token_for_user(user, base_site, token)
                                                seafile_cached_flag = True
                                            except Exception:
                                                pass

                                            r = sync_profile_name(base_site, token, profile.nickname)
                                            if r is None:
                                                seafile_profile_sync = {"success": False, "msg": "请求失败: Seafile 请求异常"}
                                            else:
                                                if 200 <= r.status_code < 300:
                                                    seafile_profile_sync = {"success": True, "msg": f"{r.status_code}"}
                                                else:
                                                    if r.status_code in (401, 403):
                                                        try:
                                                            invalidate_user_token(user, base_site)
                                                        except Exception:
                                                            pass
                                                        seafile_profile_sync = {"success": False, "msg": f"Seafile 认证失败({r.status_code})，已失效缓存，请重新登录以刷新 token"}
                                                    else:
                                                        seafile_profile_sync = {"success": False, "msg": f"{r.status_code} {getattr(r, 'text', '')}"}
                                        else:
                                            seafile_profile_sync = err or {"success": False, "msg": "未能获取 Seafile token"}
                                except Exception:
                                    seafile_profile_sync = {"success": False, "msg": "Seafile 同步异常"}
                    except Exception:
                        seafile_profile_sync = {"success": False, "msg": "Seafile 同步异常"}
                except Exception:
                    seafile_profile_sync = {"success": False, "msg": "Seafile 同步异常"}
            else:
                if not site:
                    seafile_profile_sync = {"success": False, "msg": "未配置 Seafile 站点，请在字典 cloud_type 中配置 site"}
                elif not req_password:
                    seafile_profile_sync = {"success": False, "msg": "未提供当前用户密码，跳过 Seafile 同步"}
        user.email = payload.get("email", user.email)
        user.save()
        # write_log removed: 修改个人资料
        resp_data = UserSerializer(user).data
        if seafile_profile_sync is not None:
            resp_data['seafileProfileSync'] = seafile_profile_sync
        if seafile_cached_flag:
            # 告知前端已缓存 token（布尔）
            resp_data['seafileCached'] = True
        return drf_ok(resp_data)

    @action(detail=False, methods=["put"], url_path="password")
    def change_password(self, request):
        t0 = time.perf_counter()
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
        # 尝试使用字典中的 Seafile 管理员凭据同步云端账号密码（仅当 profile.cloud_id 存在时）
        seafile_sync = None
        try:
            profile = getattr(user, 'profile', None)
            cloud_id_val = (profile.cloud_id or "").strip() if profile else ""
        except Exception:
            cloud_id_val = ""

        if cloud_id_val:
            # 读取 Seafile 管理凭据（与 reset_password 逻辑一致）
            s_site = s_user = s_pass = None
            try:
                items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
                if items:
                    for it in items:
                        label = (it.label or "").lower()
                        val = (it.value or "").strip()
                        if not s_site and ("site" in label or "站" in label or val.startswith("http")):
                            s_site = val
                            continue
                        if not s_user and ("admin" in label or "管理员" in label or "username" in label):
                            s_user = val
                            continue
                        if not s_pass and ("pass" in label or "密码" in label or "pwd" in label):
                            s_pass = val
                            continue
                    if (not s_site or not s_user or not s_pass) and items[0] and items[0].value:
                        try:
                            j = json.loads(items[0].value)
                            s_site = s_site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                            s_user = s_user or j.get("username") or j.get("user") or j.get("admin")
                            s_pass = s_pass or j.get("password") or j.get("pass") or j.get("pwd")
                        except Exception:
                            pass
            except Exception:
                items = []

            if s_site and s_user and s_pass:
                base_site = str(s_site).strip()
                if not re.match(r"^https?://", base_site, re.I):
                    base_site = "https://" + base_site
                auth_url = base_site.rstrip("/")
                if not re.search(r"api2/auth-token", auth_url, re.I):
                    auth_url = auth_url + "/api2/auth-token/"

                token = None
                try:
                    resp = requests.post(auth_url, json={"username": s_user, "password": s_pass}, timeout=10)
                    if 200 <= resp.status_code < 300:
                        try:
                            token = resp.json().get("token")
                        except Exception:
                            token = None
                except Exception:
                    token = None

                if token:
                    acct_headers = {"Authorization": f"Token {token}", "Content-Type": "application/x-www-form-urlencoded"}
                    try:
                        account_url = base_site.rstrip("/") + f"/api2/accounts/{quote(cloud_id_val)}/"
                        ar = requests.put(account_url, data={"password": new_pwd}, headers=acct_headers, timeout=10)
                        if 200 <= ar.status_code < 300:
                            seafile_sync = {"success": True, "msg": f"{ar.status_code}", "accountPut": {"success": True, "msg": f"{ar.status_code}"}}
                        else:
                            seafile_sync = {"success": False, "msg": f"{ar.status_code} {getattr(ar, 'text', '')}", "accountPut": {"success": False, "msg": f"{ar.status_code} {getattr(ar, 'text', '')}"}}
                    except Exception as e:
                        seafile_sync = {"success": False, "msg": f"请求失败: {e}", "accountPut": {"success": False, "msg": f"请求失败: {e}"}}
                else:
                    seafile_sync = {"success": False, "msg": "未能获取 Seafile token", "accountPut": {"success": False, "msg": "未能获取 Seafile token"}}
            else:
                seafile_sync = {"success": False, "msg": "未配置完整的 Seafile 管理凭据", "accountPut": {"success": False, "msg": "未配置完整的 Seafile 管理凭据"}}

        # 记录操作日志
        # write_log removed: 修改密码成功
        resp = {"message": "password changed"}
        if seafile_sync is not None:
            resp['seafileSync'] = seafile_sync
        return drf_ok(resp)

    @action(detail=False, methods=["post"], url_path="avatar")
    def upload_avatar(self, request):
        """上传头像，仅用于用户头像，不恢复通用文件上传模块。

        请求：multipart/form-data，字段名 file
        响应：{ url, name, seafileAvatarSync? }
        """
        user = request.user
        if not getattr(user, 'is_authenticated', False):
            return drf_error("未登录", status=401)
        file = request.FILES.get('file')
        if not file:
            return drf_error("未选择文件", status=400)
        # 基本校验：仅允许图片，限制大小 2MB
        content_type = getattr(file, 'content_type', '') or ''
        if not content_type.startswith('image/'):
            return drf_error("仅支持图片文件", status=400)
        max_mb = 2
        if getattr(file, 'size', 0) > max_mb * 1024 * 1024:
            return drf_error(f"图片过大，不能超过 {max_mb}MB", status=400)

        # 保存到本地存储
        from datetime import datetime
        now = datetime.utcnow()
        ext = os.path.splitext(file.name)[1] or ''
        if not ext:
            ext = {
                'image/png': '.png',
                'image/jpeg': '.jpg',
                'image/gif': '.gif',
                'image/webp': '.webp',
            }.get(content_type, '')
        rel_path = f"uploads/avatars/{now.year:04d}/{now.month:02d}/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(rel_path, file)
        media_rel = settings.MEDIA_URL.rstrip('/') + '/' + saved_path.lstrip('/')
        url = request.build_absolute_uri(media_rel)
        # write_log removed: 上传头像

        seafile_avatar_sync = None
        seafile_cached_flag = None

        # 尝试读取 site（仅 site），不使用字典中的 admin 凭据进行回退
        site = None
        try:
            items = list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
            if items:
                for it in items:
                    label = (it.label or "").lower()
                    val = (it.value or "").strip()
                    if not site and ("site" in label or "站" in label or val.startswith("http")):
                        site = val
                        break
                if (not site) and items[0] and items[0].value:
                    try:
                        j = json.loads(items[0].value)
                        site = site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                    except Exception:
                        pass
        except Exception:
            site = None

        # 前端可选提供 cloudPassword
        req_password = (request.data or {}).get('cloudPassword') or (request.data or {}).get('password') or None

        if site:
            base_site = str(site).strip()
            if not re.match(r"^https?://", base_site, re.I):
                base_site = "https://" + base_site

            try:
                from api_v1.utils.seafile import get_cached_token, get_or_fetch_user_token, sync_avatar, invalidate_user_token
            except Exception:
                get_cached_token = None
                get_or_fetch_user_token = None
                sync_avatar = None
                invalidate_user_token = None

            cached = None
            if get_cached_token:
                try:
                    cached = get_cached_token(user, base_site)
                except Exception:
                    cached = None

            if cached and sync_avatar:
                try:
                    fobj = default_storage.open(saved_path, 'rb')
                    r = sync_avatar(base_site, cached, fobj, os.path.basename(saved_path), content_type)
                    try:
                        fobj.close()
                    except Exception:
                        pass
                    if r is None:
                        seafile_avatar_sync = {"success": False, "msg": "请求失败: Seafile 请求异常"}
                    else:
                        if 200 <= r.status_code < 300:
                            seafile_avatar_sync = {"success": True, "msg": f"{r.status_code}"}
                        else:
                            if r.status_code in (401, 403):
                                try:
                                    if invalidate_user_token:
                                        invalidate_user_token(user, base_site)
                                except Exception:
                                    pass
                                seafile_avatar_sync = {"success": False, "msg": f"Seafile 认证失败({r.status_code})，已失效缓存，请重新输入密码以刷新 token"}
                            else:
                                seafile_avatar_sync = {"success": False, "msg": f"{r.status_code} {getattr(r, 'text', '')}"}
                except Exception as e:
                    seafile_avatar_sync = {"success": False, "msg": f"请求失败: {e}"}
            else:
                # cache miss -> require password. Do NOT require local check_password before attempting
                # to fetch token from Seafile; only cache token when provided password equals system password.
                if not req_password:
                    seafile_avatar_sync = {"success": False, "msg": "未提供当前用户密码，需提供以完成 Seafile 同步"}
                else:
                    if get_or_fetch_user_token:
                        token, err = get_or_fetch_user_token(user, base_site, provided_password=req_password, request=request)
                    else:
                        token, err = (None, {"success": False, "msg": "Seafile helper 未就绪"})
                    if token and sync_avatar:
                        # 成功从 Seafile 获取 token 后，缓存到后端（便于下次免密）
                        try:
                            from api_v1.utils.seafile import cache_token_for_user
                            cache_token_for_user(user, base_site, token)
                            seafile_cached_flag = True
                        except Exception:
                            pass

                        try:
                            fobj = default_storage.open(saved_path, 'rb')
                            r = sync_avatar(base_site, token, fobj, os.path.basename(saved_path), content_type)
                            try:
                                fobj.close()
                            except Exception:
                                pass
                            if r is None:
                                seafile_avatar_sync = {"success": False, "msg": "请求失败: Seafile 请求异常"}
                            else:
                                if 200 <= r.status_code < 300:
                                    seafile_avatar_sync = {"success": True, "msg": f"{r.status_code}"}
                                else:
                                    if r.status_code in (401, 403):
                                        try:
                                            if invalidate_user_token:
                                                invalidate_user_token(user, base_site)
                                        except Exception:
                                            pass
                                        seafile_avatar_sync = {"success": False, "msg": f"Seafile 认证失败({r.status_code})，已失效缓存，请重新输入密码以刷新 token"}
                                    else:
                                        seafile_avatar_sync = {"success": False, "msg": f"{r.status_code} {getattr(r, 'text', '')}"}
                        except Exception as e:
                            seafile_avatar_sync = {"success": False, "msg": f"请求失败: {e}"}
                    else:
                        seafile_avatar_sync = err or {"success": False, "msg": "未能获取 Seafile token"}
        else:
            seafile_avatar_sync = {"success": False, "msg": "未配置 Seafile 站点，请在字典 cloud_type 中配置 site"}

        # 建议裁剪信息 & 预置缩略图（头像常用 256/128/64）
        suggest = {"aspect": "1:1", "recommended": [256, 128, 64]}
        resp = {"url": url, "name": os.path.basename(saved_path), "suggestCrop": suggest}
        if seafile_avatar_sync is not None:
            resp['seafileAvatarSync'] = seafile_avatar_sync
            if seafile_cached_flag:
                resp['seafileCached'] = True
            # 写日志记录已移除: 同步 Seafile 头像 结果：{seafile_avatar_sync}
        return drf_ok(resp)

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


class ProfileViewSet(viewsets.ViewSet):
    """手机号/邮箱的验证码发送与绑定

    路由：
    - POST /users/mobile/code   发送手机验证码
    - PUT  /users/mobile        绑定手机号
    - POST /users/email/code    发送邮箱验证码
    - PUT  /users/email         绑定邮箱
    所有入参均做基本格式校验。
    """
    # 绑定手机号/邮箱应要求登录，使用全局默认权限（IsAuthenticated）

    @action(detail=False, methods=["post"], url_path="mobile/code")
    def send_mobile_code(self, request):
        s = MobileCodeSendSerializer(data=request.query_params or request.data)
        s.is_valid(raise_exception=True)
        # write_log removed: 发送手机验证码
        return drf_ok({"message": "sent"})

    @action(detail=False, methods=["put"], url_path="mobile")
    def bind_mobile(self, request):
        s = MobileBindSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        # write_log removed: 绑定手机号
        return drf_ok({"message": "mobile bound"})

    @action(detail=False, methods=["post"], url_path="email/code")
    def send_email_code(self, request):
        s = EmailCodeSendSerializer(data=request.query_params or request.data)
        s.is_valid(raise_exception=True)
        # write_log removed: 发送邮箱验证码
        return drf_ok({"message": "sent"})

    @action(detail=False, methods=["put"], url_path="email")
    def bind_email(self, request):
        s = EmailBindSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        # write_log removed: 绑定邮箱
        return drf_ok({"message": "email bound"})
