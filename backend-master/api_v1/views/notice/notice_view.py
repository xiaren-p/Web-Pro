"""通知公告 ViewSet。

承载通知公告的 CRUD、发布/撤回、已读、我的公告与导出等接口。
按钮级权限通过 ``MenuPermRequired`` + ``required_perms`` 由 ``get_permissions``
按 action / method 动态映射，超级用户与 ``admin`` 角色拥有全量可见。
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from api_v1.models import DictItem, Notice, NoticeRead, NoticeTarget
from api_v1.permissions import MenuPermRequired
from api_v1.serializers import NoticeBriefSerializer, NoticeDetailSerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


class NoticeViewSet(viewsets.ViewSet):
    """通知公告接口。

    权限映射：

    - 查询: ``sys:notice:query`` -> form / detail / list_or_create(GET)
    - 新增: ``sys:notice:add`` -> list_or_create(POST)
    - 编辑: ``sys:notice:edit`` -> update_or_delete(PUT)
    - 删除: ``sys:notice:delete`` -> update_or_delete(DELETE)
    - 发布: ``sys:notice:publish`` -> publish
    - 撤回: ``sys:notice:revoke`` -> revoke

    说明：read-all 与 my-page 仅查询，归入查询权限；普通用户若无任何按钮权限
    但被分配了"通知公告"菜单将无法访问数据（需至少具备 ``sys:notice:query``）。
    """

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        """根据 action+method 动态设置 required_perms。"""
        action_name = getattr(self, "action", None)
        method = (
            getattr(self.request, "method", "").upper()
            if hasattr(self, "request")
            else ""
        )
        required: list[str] | None = None
        # 表单/详情/管理列表仍要求查询权限（管理页面中的详情与表单）
        if action_name in ("form", "detail") or (
            action_name == "list_or_create" and method == "GET"
        ):
            required = ["sys:notice:query"]
        # 公告列表与"我的公告"对已登录用户开放（不强制按钮级权限）
        elif action_name in ("page", "my_page"):
            required = None
        elif action_name == "list_or_create" and method == "POST":
            required = ["sys:notice:add"]
        elif action_name == "update_or_delete" and method == "PUT":
            required = ["sys:notice:edit"]
        elif action_name == "update_or_delete" and method == "DELETE":
            required = ["sys:notice:delete"]
        elif action_name == "publish":
            required = ["sys:notice:publish"]
        elif action_name == "revoke":
            required = ["sys:notice:revoke"]
        elif action_name == "read_all":
            # read-all 暂归入查询权限，若无查询权限则不可标记全部已读
            required = ["sys:notice:query"]

        setattr(self, "required_perms", required)
        return super().get_permissions()

    @staticmethod
    def _serialize_brief(n: Notice) -> dict[str, Any]:
        """公告简要序列化（列表场景）。"""
        return NoticeBriefSerializer(n).data

    def _serialize_detail(self, n: Notice) -> dict[str, Any]:
        """公告详情序列化（基于简要再附带 content）。"""
        data = self._serialize_brief(n)
        data.update({"content": n.content})
        return data

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request: Request) -> Any:
        """管理端公告分页列表。

        管理员（Django 超级用户或角色 ``code=admin``）可见全部；
        其他用户仅可见已发布且（全体或指定给当前用户）的公告。
        支持 ``isRead=0`` 仅查询当前用户未读公告。
        """
        user = getattr(request, "user", None)
        from api_v1.models.system.user_profile import AdminLevel
        try:
            profile = getattr(user, "profile", None)
            is_admin_role = (
                getattr(user, "is_superuser", False)
                or (profile and profile.admin_level == AdminLevel.COMPANY_ADMIN)
            )
        except Exception:
            is_admin_role = False

        kw = request.query_params.get("title") or request.query_params.get("keywords")
        publish_status = request.query_params.get("publishStatus")

        if user and (user.is_superuser or is_admin_role):
            qs = Notice.objects.all().order_by("-id")
            if kw:
                qs = qs.filter(title__icontains=kw)
            if publish_status is not None:
                mapping = {"0": "draft", "1": "published", "2": "revoked", "-1": "revoked"}
                status_val = mapping.get(str(publish_status))
                if status_val:
                    qs = qs.filter(status=status_val)
        else:
            # 非管理员：仅返回已发布且（全体或指定给当前用户）
            qs = Notice.objects.filter(status="published").order_by("-publish_time", "-id")
            if kw:
                qs = qs.filter(title__icontains=kw)
            if user and getattr(user, "is_authenticated", False):
                qs = qs.filter(Q(target_type=1) | Q(targets__user=user)).distinct()
            else:
                qs = qs.filter(target_type=1)

        total, items, _, _ = paginate_queryset(request, qs)

        # 支持过滤已读状态：isRead=0 表示仅未读（针对当前用户）
        is_read = request.query_params.get("isRead")
        if is_read is not None and str(is_read) == "0":
            user = getattr(request, "user", None)
            if user and getattr(user, "is_authenticated", False):
                try:
                    read_ids = list(
                        NoticeRead.objects.filter(user=user).values_list("notice_id", flat=True)
                    )
                    items = [i for i in items if i.id not in read_ids]
                except Exception:
                    pass

        data = NoticeBriefSerializer(items, many=True).data
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request: Request, id: str) -> Any:
        """获取公告表单数据（用于编辑回填）。"""
        try:
            n = Notice.objects.get(pk=id)
        except Notice.DoesNotExist:
            return drf_error("未找到公告", status=404)
        return drf_ok(NoticeDetailSerializer(n).data)

    @action(detail=False, methods=["post"], url_path=r"(?P<id>[^/]+)/publish")
    def publish(self, request: Request, id: str) -> Any:
        """发布公告，写入 ``publish_time``，清空 ``revoke_time``。"""
        try:
            n = Notice.objects.get(pk=id)
        except Notice.DoesNotExist:
            return drf_error("未找到公告", status=404)
        n.status = "published"
        n.publish_time = timezone.now()
        n.revoke_time = None
        n.save()
        return drf_ok({"message": "published"})

    @action(detail=False, methods=["post"], url_path=r"(?P<id>[^/]+)/revoke")
    def revoke(self, request: Request, id: str) -> Any:
        """撤回公告，写入 ``revoke_time``。"""
        try:
            n = Notice.objects.get(pk=id)
        except Notice.DoesNotExist:
            return drf_error("未找到公告", status=404)
        n.status = "revoked"
        n.revoke_time = timezone.now()
        n.save()
        return drf_ok({"message": "revoked"})

    def detail_plain(self, request: Request, id: str) -> Any:
        """公告详情查询（手工 urls 路由，不挂 @action 避免冲突）。"""
        n = Notice.objects.get(pk=id)
        data = NoticeDetailSerializer(n).data
        return drf_ok(data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request: Request) -> Any:
        """标记当前用户所有已发布公告为已读。"""
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return drf_error("未登录", status=401)
        try:
            ids = list(Notice.objects.filter(status="published").values_list("id", flat=True))
            created = 0
            for nid in ids:
                _, created_flag = NoticeRead.objects.get_or_create(user=user, notice_id=nid)
                if created_flag:
                    created += 1
            return drf_ok({"message": "read all", "created": created})
        except Exception:
            return drf_error("标记已读失败")

    @action(detail=False, methods=["get"], url_path="my-page")
    def my_page(self, request: Request) -> Any:
        """我的公告：已发布 + 未读 + （全员或指定给我）。"""
        qs = Notice.objects.filter(status="published").order_by("-publish_time", "-id")

        kw = request.query_params.get("title") or request.query_params.get("keywords")
        if kw:
            qs = qs.filter(title__icontains=kw)

        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            read_ids = NoticeRead.objects.filter(user=user).values_list("notice_id", flat=True)
            qs = qs.exclude(id__in=read_ids)
            qs = qs.filter(Q(target_type=1) | Q(targets__user=user)).distinct()
        else:
            # 未登录用户仅可见全员（理论上未登录无法访问此接口，由 permission 控制）
            qs = qs.filter(target_type=1)

        total, items, _, _ = paginate_queryset(request, qs)
        data = NoticeBriefSerializer(items, many=True).data
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request: Request) -> Any:
        """GET: 全量列表；POST: 新增公告草稿。"""
        if request.method.lower() == "get":
            items = Notice.objects.all().order_by("-id")
            return drf_ok([self._serialize_brief(n) for n in items])

        p = request.data.copy()
        target_type = int(p.get("targetType") or 1)
        target_user_ids = p.get("targetUserIds", [])

        n = Notice.objects.create(
            title=p.get("title") or "",
            content=p.get("content") or "",
            type=p.get("type") or "general",
            level=p.get("level") or "L",
            target_type=target_type,
            status="draft",
            creator=request.user
            if getattr(request, "user", None) and request.user.is_authenticated
            else None,
        )

        # 处理指定用户关联
        if target_type == 2 and target_user_ids and isinstance(target_user_ids, list):
            targets = [NoticeTarget(notice=n, user_id=uid) for uid in target_user_ids]
            if targets:
                NoticeTarget.objects.bulk_create(targets)

        return drf_ok(self._serialize_detail(n), status=201)

    @action(detail=True, methods=["post"], url_path="read")
    def read(self, request: Request, id: str) -> Any:
        """标记单条公告为已读（对当前用户）。"""
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return drf_error("未登录", status=401)
        try:
            NoticeRead.objects.get_or_create(user=user, notice_id=id)
            return drf_ok({"read": True})
        except Exception:
            return drf_error("标记已读失败")

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request: Request, ids: str) -> Any:
        """根据 ID 进行 PUT 编辑（首个 ID）或 DELETE 批量删除（逗号分隔）。"""
        if request.method.lower() == "delete":
            id_list = [i for i in ids.split(",") if i]
            cnt, _ = Notice.objects.filter(id__in=id_list).delete()
            return drf_ok({"deleted": cnt})

        if request.method.lower() == "put":
            first_id = ids.split(",")[0]
            try:
                n = Notice.objects.get(pk=first_id)
            except Notice.DoesNotExist:
                return drf_error("未找到公告", status=404)

            if n.status == "published":
                return drf_error("已发布的公告不可编辑", status=400)

            p = request.data.copy()
            if "title" in p:
                n.title = p.get("title") or n.title
            if "content" in p:
                n.content = p.get("content") or n.content
            if "type" in p:
                n.type = p.get("type") or n.type
            if "level" in p:
                n.level = p.get("level") or "L"

            if "targetType" in p:
                n.target_type = int(p.get("targetType"))
                n.save()
                # 更新关联用户
                NoticeTarget.objects.filter(notice=n).delete()
                if n.target_type == 2:
                    t_ids = p.get("targetUserIds", [])
                    if isinstance(t_ids, list) and t_ids:
                        targets = [NoticeTarget(notice=n, user_id=uid) for uid in t_ids]
                        NoticeTarget.objects.bulk_create(targets)
            else:
                n.save()

            return drf_ok(self._serialize_detail(n))

    @action(detail=False, methods=["get"], url_path="export")
    def export_data(self, request: Request) -> Any:
        """导出公告 Excel 文件。

        优先使用 ``ids`` 精确导出；其次 ``onlyMine=1`` 导出当前用户可见公告；
        否则按筛选条件全量导出。时间格式 ``YYYY-MM-DD HH:MM:SS`` 仅用于 Excel
        二进制文件展示，非 API JSON 数据，不违反"后端定型"原则。
        """
        try:
            from openpyxl import Workbook
        except ImportError:
            return drf_error("未安装 openpyxl 库")

        qs = Notice.objects.all().order_by("-id")

        # 优先支持 ids 参数（前端传逗号分隔 id 列表）
        ids_param = request.query_params.get("ids")
        only_mine = request.query_params.get("onlyMine")
        try:
            if ids_param:
                ids_list = [i for i in re.split(r"\s*,\s*", ids_param) if i]
                if ids_list:
                    qs = qs.filter(id__in=ids_list).order_by("-id")
            elif only_mine and str(only_mine).lower() in ("1", "true", "yes"):
                user = getattr(request, "user", None)
                if not user or not getattr(user, "is_authenticated", False):
                    return drf_error("未登录", status=401)
                qs = (
                    Notice.objects.filter(status="published")
                    .filter(Q(target_type=1) | Q(targets__user=user))
                    .distinct()
                    .order_by("-publish_time", "-id")
                )
        except Exception:
            qs = Notice.objects.all().order_by("-id")

        # 普通筛选参数（在没有使用 ids 精确控制时仍适用）
        kw = request.query_params.get("title")
        if kw:
            qs = qs.filter(title__icontains=kw)

        publish_status = request.query_params.get("publishStatus")
        if publish_status is not None and str(publish_status) != "":
            mapping = {"0": "draft", "1": "published", "2": "revoked", "-1": "revoked"}
            status_val = mapping.get(str(publish_status))
            if status_val:
                qs = qs.filter(status=status_val)

        n_type = request.query_params.get("type")
        if n_type:
            qs = qs.filter(type=n_type)

        n_level = request.query_params.get("level")
        if n_level:
            qs = qs.filter(level=n_level)

        target_type = request.query_params.get("targetType")
        if target_type:
            try:
                qs = qs.filter(target_type=int(target_type))
            except Exception:
                pass

        # 预加载字典缓存
        type_map: dict[str, str] = {}
        level_map: dict[str, str] = {}
        try:
            for item in DictItem.objects.filter(dict_type__code="notice_type", status=True):
                type_map[item.value] = item.label
            for item in DictItem.objects.filter(dict_type__code="notice_level", status=True):
                level_map[item.value] = item.label
        except Exception:
            pass

        wb = Workbook()
        ws = wb.active
        ws.title = "通知公告"

        headers = [
            "通知标题", "通知类型", "发布人", "通知等级",
            "目标账号", "目标昵称", "通知内容", "通知时间(+08:00)",
        ]
        ws.append(headers)

        for n in qs:
            t_label = type_map.get(n.type, n.type)
            l_label = level_map.get(n.level, n.level)

            target_accs = "全体"
            target_nicks = "全体"
            if n.target_type == 2:
                targets = list(n.targets.all().select_related("user", "user__profile"))
                if targets:
                    target_accs = ",".join([t.user.username for t in targets if t.user])
                    target_nicks = ",".join([
                        getattr(t.user.profile, "nickname", "") or t.user.username
                        for t in targets
                        if t.user and hasattr(t.user, "profile")
                    ])
                else:
                    target_accs = "无指定用户"
                    target_nicks = "无指定用户"

            content_text = ""
            if n.content:
                # 简单去除 HTML 标签后输出纯文本
                content_text = re.sub(r"<[^>]+>", "", n.content).replace("\n", "").strip()

            # Excel 单元格使用字符串时间格式（导出场景，不是 API JSON）
            if n.publish_time:
                time_str = n.publish_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = n.created_at.strftime("%Y-%m-%d %H:%M:%S")

            ws.append([
                n.title,
                t_label,
                getattr(n.creator, "username", "") if n.creator else "",
                l_label,
                target_accs,
                target_nicks,
                content_text,
                time_str,
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = urllib.parse.quote("通知公告导出.xlsx")
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
        wb.save(response)
        return response
