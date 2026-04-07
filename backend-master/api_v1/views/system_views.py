import json
import time
import re
from datetime import datetime, timedelta

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from api_v1.permissions import MenuPermRequired

from api_v1.models import (
    Menu, Department, DictType, DictItem, Config, OperLog
)
from api_v1.serializers import (
    MenuSerializer, DeptSerializer, DictTypeSerializer, DictItemSerializer, OperLogSerializer
)
from api_v1.utils.responses import drf_ok, drf_error
from api_v1.utils.pagination import paginate_queryset
# `write_log` 日志调用已由批量替换移除，以避免在视图中直接写操作日志。
# 如果需要恢复日志功能，请在此处重新导入并在需要的位置恢复调用。


class MenuViewSet(viewsets.ViewSet):
    """菜单与动态路由接口"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action = getattr(self, 'action', None)
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        required = None
        # 查询：列表 list_or_create(GET), tree, form 使用 菜单查询 权限；
        # options 下拉用于角色分配菜单场景，允许具备 菜单查询 或 角色编辑 任一权限访问（OR 逻辑）
        if action in ("list_or_create", "tree", "form") and method == 'GET':
            required = ["sys:menu:query"]
        elif action == "options" and method == 'GET':
            required = ["sys:menu:query", "sys:role:edit"]
        # 新增
        elif action == "list_or_create" and method == 'POST':
            required = ["sys:menu:add"]
        # 更新
        elif action == "update_or_delete" and method == 'PUT':
            required = ["sys:menu:edit"]
        # 删除
        elif action == "update_or_delete" and method == 'DELETE':
            required = ["sys:menu:delete"]
        # routes 接口：用于动态路由加载，需要登录但不强制按钮级菜单权限（前端根据已分配菜单自行构建）
        elif action == "routes":
            required = None
        setattr(self, 'required_perms', required)
        return super().get_permissions()

    @staticmethod
    def _serialize(m: Menu):
        # routeName 仅对“菜单”类型生效（type=2）。目录/按钮/外链在管理列表中不显示路由名称。
        def compute_route_name():
            if m.type != 2:
                return ""
            try:
                if m.route_name:
                    return m.route_name
                if m.component:
                    last = m.component.split('/')[-1]
                    return (last[:1].upper() + last[1:]) if last else f"Menu{m.id}"
                return f"Menu{m.id}"
            except Exception:
                return f"Menu{m.id}"

        return {
            "id": m.id,
            "parentId": m.parent_id,
            "name": m.name,
            "type": m.type,
            "routeName": compute_route_name(),
            "path": m.path,
            "component": m.component,
            "perms": m.perms,
            "icon": m.icon,
            "sort": m.order_num,
            "visible": 1 if m.visible else 0,
            "status": 1 if m.status else 0,
        }

    @staticmethod
    def _build_routes(nodes):
        # 仅目录/菜单生成路由，按钮(3)跳过
        by_parent = {}
        for m in nodes:
            if m.type == 3:
                continue
            pid = m.parent_id or 0
            by_parent.setdefault(pid, []).append(m)

        def build(pid=None):
            result = []
            for m in by_parent.get(pid or 0, []):
                route = {
                    "name": (m.route_name or f"Menu{m.id}"),
                    "path": m.path or (f"/m{m.id}" if m.parent_id is None else m.path or f"m{m.id}"),
                    "component": m.component if m.component else ("Layout" if m.type == 1 else ""),
                    "meta": {
                        "title": m.name,
                        "icon": m.icon or None,
                        "hidden": False if m.visible else True,
                    },
                }
                # 外链型：前端可使用 meta.link 或特殊处理，这里标记，实际消费由前端决定
                if m.type == 4:
                    # 外链菜单：若 path 是绝对 URL，转换为内部占位路径 + meta.link
                    original_path = m.path or ''
                    import re
                    if re.match(r'^https?://', original_path):
                        # 使用稳定且唯一的内部占位路径，避免与其它路由冲突
                        internal_path = f"/ext-{m.id}"
                        route["path"] = internal_path
                        route["component"] = "external/redirect"
                        route["meta"]["link"] = original_path
                    route["meta"]["external"] = True
                children = build(m.id)
                if children:
                    route["children"] = children
                result.append(route)
            return result

        return build(None)

    @action(detail=False, methods=["get"], url_path="routes")
    def routes(self, request):
        user = getattr(request, 'user', None)
        # 全部启用菜单
        all_active = list(Menu.objects.filter(status=True).order_by("order_num", "id"))
        if not user or not getattr(user, 'is_authenticated', False):
            return drf_error("未登录", status=401)
        # 管理员（Django 超级用户 或 角色 code=admin）返回全部
        is_admin_role = False
        try:
            profile = getattr(user, 'profile', None)
            if profile:
                is_admin_role = profile.roles.filter(code='admin').exists()
        except Exception:
            is_admin_role = False
        # 已不再由后端强制插入“文件管理”外链，改为在菜单管理中自行添加外链（type=4）。

        if user.is_superuser or is_admin_role:
            return drf_ok(self._build_routes(all_active))

        # 计算用户角色关联到的菜单，并补齐所有上级目录，保证树结构完整
        role_ids = []
        if profile:
            role_ids = list(profile.roles.values_list('id', flat=True))
        if not role_ids:
            return drf_ok([])
        assigned = list(Menu.objects.filter(status=True, roles__in=role_ids).distinct())
        if not assigned:
            return drf_ok([])
        by_id = {m.id: m for m in all_active}
        selected = {m.id for m in assigned}
        # 向上补全父级
        for m in list(assigned):
            p = m.parent
            while p is not None:
                if p.id in selected:
                    break
                selected.add(p.id)
                p = p.parent
        nodes = [by_id[i] for i in selected if i in by_id]
        nodes.sort(key=lambda x: (x.order_num, x.id))
        return drf_ok(self._build_routes(nodes))

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == 'get':
            qs = Menu.objects.all().order_by("order_num", "id")
            # 关键字查询：支持 name/path/component/perms
            keyword = request.query_params.get("keyword") or request.query_params.get("keywords")
            if isinstance(keyword, str):
                kw = keyword.strip()
                if kw:
                    qs = qs.filter(
                        Q(name__icontains=kw) |
                        Q(path__icontains=kw) |
                        Q(component__icontains=kw) |
                        Q(perms__icontains=kw)
                    )
            return drf_ok([self._serialize(m) for m in qs])
        # create
        import time
        t0 = time.perf_counter()
        p = request.data.copy()
        m = Menu.objects.create(
            name=p.get("name") or "",
            type=int(p.get("type") or 2),
            route_name=p.get("routeName") or "",
            path=p.get("path") or "",
            component=p.get("component") or "",
            perms=p.get("perms") or "",
            icon=p.get("icon") or "",
            parent=Menu.objects.filter(pk=p.get("parentId")).first() if p.get("parentId") else None,
            order_num=int(p.get("sort") or 0),
            visible=bool(int(p.get("visible", 1))),
        )
        # write_log removed: 写入菜单新增日志已被移除
        return drf_ok(self._serialize(m), status=201)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        # 树形：/menus/tree?keywords=...
        qs = Menu.objects.all().order_by("order_num", "id")
        keyword = request.query_params.get("keyword") or request.query_params.get("keywords")
        is_search = False
        if isinstance(keyword, str):
            kw = keyword.strip()
            if kw:
                is_search = True
                qs = qs.filter(
                    Q(name__icontains=kw) |
                    Q(path__icontains=kw) |
                    Q(component__icontains=kw) |
                    Q(perms__icontains=kw)
                )
        
        nodes = [self._serialize(m) for m in qs]
        
        # 复用 DeptViewSet._build_tree 的逻辑（或自行实现）
        def build(pid=None):
            res = []
            for node in nodes:
                # 需注意：如果是搜索结果，父节点可能不在结果中，无法组树 -> 直接返回扁平列表
                if is_search:
                    return nodes 

                current_pid = node["parentId"]
                if current_pid == pid:
                    children = build(node["id"])
                    if children:
                        node["children"] = children
                    res.append(node)
            return res

        return drf_ok(build(None))

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        try:
            m = Menu.objects.get(pk=id)
        except Menu.DoesNotExist:
            return drf_error("未找到菜单", status=404)
        return drf_ok(self._serialize(m))

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<id>[^/]+)")
    def update_or_delete(self, request, id: str):
        if request.method.lower() == 'put':
            import time
            t0 = time.perf_counter()
            try:
                m = Menu.objects.get(pk=id)
            except Menu.DoesNotExist:
                # write_log removed: 更新菜单失败：未找到（ID={id}）
                return drf_error("未找到菜单", status=404)
            p = request.data.copy()
            # 基本字段
            if "name" in p:
                m.name = p.get("name") or m.name
            if "type" in p:
                try:
                    m.type = int(p.get("type"))
                except Exception:
                    pass
            # 路由名称（前端字段 routeName）
            if "routeName" in p:
                m.route_name = p.get("routeName") or ""
            if "path" in p:
                m.path = p.get("path") or m.path
            if "component" in p:
                m.component = p.get("component") or m.component
            if "perms" in p:
                m.perms = p.get("perms") or m.perms
            if "icon" in p:
                m.icon = p.get("icon") or m.icon
            if "parentId" in p:
                m.parent = Menu.objects.filter(pk=p.get("parentId")).first() if p.get("parentId") else None
            if "sort" in p:
                m.order_num = int(p.get("sort") or 0)
            if "visible" in p:
                m.visible = bool(int(p.get("visible")))
            if "status" in p:
                m.status = bool(int(p.get("status")))
            m.save()
            # write_log removed: 更新菜单：{m.name}（ID={m.id}）
            return drf_ok(self._serialize(m))
        
        # delete
        import time
        t0 = time.perf_counter()
        # 检查是否含有子菜单
        if Menu.objects.filter(parent_id=id).exists():
            # write_log removed: 删除菜单失败：存在子菜单（ID={id}）
            return drf_error("存在子菜单，无法删除", status=400)
        Menu.objects.filter(pk=id).delete()
        # write_log removed: 删除菜单（ID={id}）
        return drf_ok(status=204)

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        # 默认返回所有节点（用于权限分配），若指定 onlyParent=true 则仅返回目录和菜单（用于上级菜单选择）
        only_parent = request.query_params.get("onlyParent")
        if only_parent and str(only_parent).lower() == 'true':
            qs = Menu.objects.filter(type__in=[1, 2]).order_by("order_num", "id")
        else:
            qs = Menu.objects.all().order_by("order_num", "id")
        
        def build(pid=None):
            res = []
            for m in qs:
                if m.parent_id == pid:
                    children = build(m.id)
                    item = {
                        "value": m.id,
                        "label": m.name,
                    }
                    if children:
                        item["children"] = children
                    res.append(item)
            return res
        return drf_ok(build(None))
    
    
class DeptViewSet(viewsets.ViewSet):
    """部门管理接口"""
    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action = getattr(self, 'action', None)
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        required = None
        # 查询相关：列表、树、下拉、表单
        if action in ("list_or_create", "tree", "options", "form") and method == 'GET':
            required = ["sys:dept:query"]
        # 新增
        elif action == "list_or_create" and method == 'POST':
            required = ["sys:dept:add"]
        # 更新
        elif action == "update_or_delete" and method == 'PUT':
            required = ["sys:dept:edit"]
        # 删除
        elif action == "update_or_delete" and method == 'DELETE':
            required = ["sys:dept:delete"]
        setattr(self, 'required_perms', required)
        return super().get_permissions()

    def _build_tree(self, nodes):
        by_parent = {}
        for d in nodes:
            pid = d.parent_id or 0
            by_parent.setdefault(pid, []).append(d)

        def build(pid=None, path=None):
            if path is None:
                path = set()
            res = []
            for d in by_parent.get(pid or 0, []):
                if d.id in path:
                    continue
                new_path = set(path)
                new_path.add(d.id)
                item = {
                    "id": d.id,
                    "parentId": d.parent_id,
                    "name": d.name,
                    "code": getattr(d, 'code', ''),
                    "status": 1 if d.status else 0,
                    "sort": d.order_num,
                    "children": build(d.id, new_path),
                }
                res.append(item)
            return res

        return build(None)

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == 'get':
            qs = Department.objects.all().order_by("order_num", "id")
            # 关键字：name/code 模糊
            keyword = request.query_params.get("keyword") or request.query_params.get("keywords")
            if isinstance(keyword, str):
                kw = keyword.strip()
                if kw:
                    qs = qs.filter(Q(name__icontains=kw) | Q(code__icontains=kw))
            # 状态过滤：1/0
            status_val = request.query_params.get("status")
            if status_val is not None and status_val != "":
                try:
                    qs = qs.filter(status=bool(int(status_val)))
                except Exception:
                    pass
            data = DeptSerializer(qs, many=True).data
            return drf_ok(data)
        import time
        t0 = time.perf_counter()
        payload = request.data.copy()
        name = payload.get("name")
        parent_id = payload.get("parentId")
        sort = payload.get("sort", 0)
        status = payload.get("status", 1)
        code = payload.get("code", "")
        dept = Department.objects.create(
            name=name or "",
            parent=Department.objects.filter(pk=parent_id).first() if parent_id else None,
            order_num=int(sort or 0),
            code=code or "",
            status=bool(int(status)) if isinstance(status, (str, int)) else bool(status),
        )
        # write_log removed: 新增部门：{dept.name}（ID={dept.id}）
        return drf_ok({"id": dept.id}, status=201)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        try:
            qs = Department.objects.all().order_by("order_num", "id")
            return drf_ok(self._build_tree(list(qs)))
        except Exception as e:
            # write_log removed: 查询部门树失败：{e}
            return drf_error("服务器内部错误", status=500)

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        qs = Department.objects.filter(status=True).order_by("order_num", "id")
        data = [
            {"label": d.name, "value": d.id}
            for d in qs
        ]
        return drf_ok(data)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        try:
            d = Department.objects.get(pk=id)
        except Department.DoesNotExist:
            return drf_error("未找到部门", status=404)
        return drf_ok({
            "id": d.id, "name": d.name, "code": getattr(d, 'code', ''), "parentId": d.parent_id, "status": 1 if d.status else 0, "sort": d.order_num
        })

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == 'put':
            first_id = ids.split(',')[0]
            try:
                d = Department.objects.get(pk=first_id)
            except Department.DoesNotExist:
                return drf_error("未找到部门", status=404)
            payload = request.data.copy()
            d.name = payload.get("name", d.name)
            parent_id = payload.get("parentId")
            # 校验：禁止将上级设置为自身或其子孙，避免循环
            if parent_id:
                try:
                    pid_int = int(parent_id)
                except Exception:
                    pid_int = None
                if pid_int and pid_int == d.id:
                    return drf_error("上级部门不能为自身", status=400)
                new_parent = Department.objects.filter(pk=parent_id).first()
                cur = new_parent
                while cur is not None:
                    if cur.id == d.id:
                        return drf_error("上级部门不能为其子孙节点", status=400)
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
            # write_log removed: 更新部门：{d.name}（ID={d.id}）
            return drf_ok({"id": d.id})
        id_list = [i for i in ids.split(',') if i]
        Department.objects.filter(id__in=id_list).delete()
        # write_log removed: 删除部门：{ids}
        return drf_ok(status=204)


class DictViewSet(viewsets.ViewSet):
    """字典与字典项接口"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action = getattr(self, 'action', None)
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        required = None
        # 字典类型分页 / 列表 / 表单 / 字典项分页 / 字典项表单 / 选项 查询权限
        if action in ("page", "list_or_create", "form", "items_page", "item_form") and method == 'GET':
            required = ["sys:dict:query"]
        # 字典项选项接口单独使用 sys:dict:item 更细粒度权限（仅访问字典数据，不必具备字典类型查询权限）
        elif action == "item_options" and method == 'GET':
            required = ["sys:dict:item"]
        # 字典类型新增
        elif action == "list_or_create" and method == 'POST':
            required = ["sys:dict:add"]
        # 字典类型更新
        elif action == "update_or_delete" and method == 'PUT':
            required = ["sys:dict:edit"]
        # 字典类型删除
        elif action == "update_or_delete" and method == 'DELETE':
            required = ["sys:dict:delete"]
        # 字典项新增
        elif action == "items_list_or_create" and method == 'POST':
            required = ["sys:dict:add"]
        # 字典项更新
        elif action == "item_update_or_delete" and method == 'PUT':
            required = ["sys:dict:edit"]
        # 字典项删除
        elif action == "item_update_or_delete" and method == 'DELETE':
            required = ["sys:dict:delete"]
        setattr(self, 'required_perms', required)
        return super().get_permissions()

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        # pageNum/pageSize/keywords
        qs = DictType.objects.all().order_by("id")
        kw = request.query_params.get("keywords")
        if kw:
            qs = qs.filter(Q(name__icontains=kw) | Q(code__icontains=kw))
        total, items, _, _ = paginate_queryset(request, qs)
        data = DictTypeSerializer(items, many=True).data
        # 统一将 status 转换为 1/0，避免前端严格比较 === 1 时被识别为禁用
        for d in data:
            # d['status'] 可能是 True/False
            try:
                d['status'] = 1 if d.get('status') else 0
            except Exception:
                d['status'] = 0
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == 'get':
            items = DictType.objects.all().order_by("id")
            data = [{"id": d.id, "name": d.name, "dictCode": d.code, "status": 1 if d.status else 0} for d in items]
            return drf_ok(data)
        # create
        import time
        t0 = time.perf_counter()
        payload = request.data.copy()
        name = payload.get("name")
        code = payload.get("dictCode") or payload.get("code")
        status_raw = payload.get("status", 1)
        def parse_status(v, default=True):
            if v in (None, "", "null"):
                return default
            if isinstance(v, (str, int)):
                try:
                    return bool(int(v))
                except Exception:
                    return default
            return bool(v)
        dt = DictType.objects.create(name=name or "", code=code or "", status=parse_status(status_raw, True))
        # write_log removed: 新增字典：{dt.code}（{dt.name}，ID={dt.id}）
        return drf_ok({"id": dt.id}, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        try:
            d = DictType.objects.get(pk=id)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        return drf_ok({"id": d.id, "name": d.name, "dictCode": d.code, "status": 1 if d.status else 0})

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == 'put':
            first_id = ids.split(',')[0]
            try:
                d = DictType.objects.get(pk=first_id)
            except DictType.DoesNotExist:
                return drf_error("未找到字典", status=404)
            payload = request.data.copy()
            if "name" in payload:
                d.name = payload.get("name") or d.name
            if "dictCode" in payload or "code" in payload:
                d.code = payload.get("dictCode") or payload.get("code") or d.code
            if "status" in payload:
                s = payload.get("status")
                def parse_status(v, default=d.status):
                    if v in (None, "", "null"):
                        return default
                    if isinstance(v, (str, int)):
                        try:
                            return bool(int(v))
                        except Exception:
                            return default
                    return bool(v)
                d.status = parse_status(s, d.status)
            d.save()
            # write_log removed: 更新字典：{d.code}（{d.name}，ID={d.id}）
            return drf_ok({"id": d.id})
        id_list = [i for i in ids.split(',') if i]
        DictType.objects.filter(id__in=id_list).delete()
        # write_log removed: 删除字典：{ids}
        return drf_ok(status=204)

    # dict items
    @action(detail=False, methods=["get", "post"], url_path=r"(?P<dict_code>[^/]+)/items")
    def items_list_or_create(self, request, dict_code: str):
        try:
            dt = DictType.objects.get(code=dict_code)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        # 若字典类型被禁用，阻止访问或创建其字典项
        if not dt.status:
            return drf_error("字典已禁用", status=403)
        if request.method.lower() == 'get':
            items = DictItem.objects.filter(dict_type=dt).order_by("sort", "id")
            data = DictItemSerializer(items, many=True).data
            return drf_ok(data)
        # create item
        import time
        t0 = time.perf_counter()
        payload = request.data.copy()
        i = DictItem.objects.create(
            dict_type=dt,
            label=payload.get("label") or "",
            value=payload.get("value") or "",
            sort=int(payload.get("sort") or 0),
            status=(lambda v: (False if v in ("0", 0) else True) if v not in (None, "", "null") else True)(payload.get("status", 1)),
            tag_type=payload.get("tagType") or payload.get("tag_type") or "",
        )
        # write_log removed: 新增字典项：{dt.code} -> {i.label}（ID={i.id}）
        return drf_ok({"id": i.id}, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<dict_code>[^/]+)/items/page")
    def items_page(self, request, dict_code: str):
        try:
            dt = DictType.objects.get(code=dict_code)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        if not dt.status:
            return drf_error("字典已禁用", status=403)
        qs = DictItem.objects.filter(dict_type=dt).order_by("sort", "id")
        kw = request.query_params.get("keywords")
        if kw:
            qs = qs.filter(Q(label__icontains=kw) | Q(value__icontains=kw))
        total, items, _, _ = paginate_queryset(request, qs)
        data = DictItemSerializer(items, many=True).data
        # 兜底：若序列化器未生效或其他来源数据，确保 status 数值化
        for it in data:
            try:
                it["status"] = 1 if it.get("status") in (True, 1, "1", "true", "True") else 0
            except Exception:
                it["status"] = 0
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get"], url_path=r"(?P<dict_code>[^/]+)/items/(?P<item_id>[^/]+)/form")
    def item_form(self, request, dict_code: str, item_id: str):
        try:
            dt = DictType.objects.get(code=dict_code)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        if not dt.status:
            return drf_error("字典已禁用", status=403)
        try:
            i = DictItem.objects.get(pk=item_id, dict_type=dt)
        except DictItem.DoesNotExist:
            return drf_error("未找到字典项", status=404)
        return drf_ok({"id": i.id, "label": i.label, "value": i.value, "status": 1 if i.status else 0, "sort": i.sort, "tagType": getattr(i, 'tag_type', '')})

    @action(detail=False, methods=["get"], url_path=r"(?P<dict_code>[^/]+)/items/options")
    def item_options(self, request, dict_code: str):
        try:
            dt = DictType.objects.get(code=dict_code)
            if not dt.status:
                return drf_ok([])  # 禁用字典返回空选项，避免表单误用
            items = DictItem.objects.filter(dict_type=dt, status=True).order_by("sort", "id")
            data = [{"label": i.label, "value": i.value} for i in items]
            return drf_ok(data)
        except DictType.DoesNotExist:
            # 内置兜底：常用字典 gender 缺失时返回默认选项
            if dict_code == 'gender':
                return drf_ok([
                    {"label": "男", "value": 1},
                    {"label": "女", "value": 2},
                    {"label": "保密", "value": 0},
                ])
            return drf_error("未找到字典", status=404)

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<dict_code>[^/]+)/items/(?P<item_id>[^/]+)")
    def item_update_or_delete(self, request, dict_code: str, item_id: str):
        try:
            dt = DictType.objects.get(code=dict_code)
        except DictType.DoesNotExist:
            return drf_error("未找到字典", status=404)
        if not dt.status:
            return drf_error("字典已禁用", status=403)
        if request.method.lower() == 'put':
            try:
                i = DictItem.objects.get(pk=item_id, dict_type=dt)
            except DictItem.DoesNotExist:
                return drf_error("未找到字典项", status=404)
            payload = request.data.copy()
            if "label" in payload:
                i.label = payload.get("label") or i.label
            if "value" in payload:
                i.value = payload.get("value") or i.value
            if "sort" in payload:
                i.sort = int(payload.get("sort") or 0)
            if "status" in payload:
                s = payload.get("status")
                if s in (None, "", "null"):
                    pass  # 忽略空值，不修改
                else:
                    try:
                        i.status = bool(int(s))
                    except Exception:
                        i.status = True if s else i.status
            if "tagType" in payload or "tag_type" in payload:
                tv = payload.get("tagType") or payload.get("tag_type")
                i.tag_type = tv or ""
            i.save()
            # write_log removed: 更新字典项：{dt.code} -> {i.label}（ID={i.id}）
            return drf_ok({"id": i.id})
        # delete supports ids path, but this endpoint targets single id by design; handle multi-ids too
        id_list = [i for i in item_id.split(',') if i]
        DictItem.objects.filter(dict_type=dt, id__in=id_list).delete()
        # write_log removed: 删除字典项：{dt.code} -> {item_id}
        return drf_ok(status=204)


class LogViewSet(viewsets.ViewSet):
    """操作/访问日志接口"""

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action = getattr(self, 'action', None)
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        required = None
        # 页面分页列表查看
        if action == 'page' and method == 'GET':
            required = ['sys:log:view']
        # 访问趋势图
        elif action == 'visit_trend' and method == 'GET':
            required = ['sys:log:trend']
        # 访问统计
        elif action == 'visit_stats' and method == 'GET':
            required = ['sys:log:stats']
        setattr(self, 'required_perms', required)
        return super().get_permissions()

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        qs = OperLog.objects.all().order_by("-id")
        # 关键字（匹配 module/action/operator/ip）
        keywords = request.query_params.get('keywords')
        if keywords:
            qs = qs.filter(
                Q(module__icontains=keywords) |
                Q(action__icontains=keywords) |
                Q(operator__icontains=keywords) |
                Q(ip__icontains=keywords)
            )
        # 时间范围 createTime[]=start&createTime[]=end （YYYY-MM-DD）
        date_range = request.query_params.getlist('createTime[]') or request.query_params.getlist('createTime')
        if date_range and len(date_range) >= 2 and date_range[0] and date_range[1]:
            from datetime import datetime, timedelta
            try:
                start = datetime.strptime(date_range[0], '%Y-%m-%d')
                end = datetime.strptime(date_range[1], '%Y-%m-%d') + timedelta(days=1)
                qs = qs.filter(created_at__gte=start, created_at__lt=end)
            except Exception:
                pass
        total, items, _, _ = paginate_queryset(request, qs)
        # 序列化并进行字段别名转换：created_at -> createTime, elapsed_ms -> executionTime
        raw = OperLogSerializer(items, many=True).data
        # 轻量 UA 解析与 IP 区域判断（避免引入第三方依赖）
        import re
        def parse_browser(ua: str) -> str:
            if not ua:
                return ""
            ua = str(ua)
            try:
                # 顺序很重要：Edge 包含 Chrome 标记，先匹配特定浏览器
                m = re.search(r'Edg/([\d\.]+)', ua)
                if m:
                    return f'Edge {m.group(1)}'
                m = re.search(r'OPR/([\d\.]+)', ua)
                if m:
                    return f'Opera {m.group(1)}'
                m = re.search(r'Chrome/([\d\.]+)', ua)
                if m and 'Chromium' not in ua and 'Edg/' not in ua:
                    return f'Chrome {m.group(1)}'
                m = re.search(r'Firefox/([\d\.]+)', ua)
                if m:
                    return f'Firefox {m.group(1)}'
                # Safari 版本号使用 Version/xx 而非 Safari/xx
                if 'Safari/' in ua and 'Chrome/' not in ua and 'Chromium' not in ua:
                    m = re.search(r'Version/([\d\.]+)', ua)
                    if m:
                        return f'Safari {m.group(1)}'
                    return 'Safari'
            except Exception:
                pass
            return ''

        def parse_os(ua: str) -> str:
            if not ua:
                return ""
            ua = str(ua)
            try:
                # Windows NT 10.0; Win64; x64
                m = re.search(r'Windows NT ([\d\.]+)', ua)
                if m:
                    ver_map = {
                        '10.0': '10/11',  # 10.0 可同时对应 Win10/11，细分需更复杂逻辑
                        '6.3': '8.1',
                        '6.2': '8',
                        '6.1': '7',
                        '6.0': 'Vista',
                        '5.1': 'XP',
                    }
                    ver_raw = m.group(1)
                    ver = ver_map.get(ver_raw, ver_raw)
                    return f'Windows {ver}'
                m = re.search(r'Android ([\d\.]+)', ua)
                if m:
                    return f'Android {m.group(1)}'
                m = re.search(r'iPhone OS ([\d_]+)', ua)
                if m:
                    return f'iOS {m.group(1).replace("_", ".")}'
                m = re.search(r'iPad; CPU OS ([\d_]+)', ua)
                if m:
                    return f'iPadOS {m.group(1).replace("_", ".")}'
                m = re.search(r'Mac OS X ([\d_]+)', ua)
                if m:
                    return f'macOS {m.group(1).replace("_", ".")}'
                if 'Linux' in ua:
                    return 'Linux'
            except Exception:
                pass
            return ''

        def parse_region(ip: str) -> str:
            if not ip:
                return ''
            ip = str(ip)
            try:
                if ip.startswith('127.') or ip == '::1':
                    return '本机'
                # 私有网段
                if ip.startswith('10.') or ip.startswith('192.168.'):
                    return '内网'
                if ip.startswith('172.'):
                    try:
                        seg = int(ip.split('.')[1])
                        if 16 <= seg <= 31:
                            return '内网'
                    except Exception:
                        pass
            except Exception:
                pass
            return '未知'

        data = []
        for r in raw:
            ua = r.get('user_agent')
            ip = r.get('ip')
            data.append({
                'id': r.get('id'),
                'module': r.get('module'),
                'content': r.get('action') or '',
                'operator': r.get('operator'),
                'ip': ip,
                'region': parse_region(ip),
                'browser': parse_browser(ua),
                'os': parse_os(ua),
                'createTime': r.get('created_at'),
                'executionTime': r.get('elapsed_ms'),
            })
        return drf_ok({'total': total, 'list': data})

    @action(detail=False, methods=["get"], url_path="visit-trend")
    def visit_trend(self, request):
        import datetime
        from django.db.models.functions import TruncDate
        from django.db.models import Count
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=6)
        qs = OperLog.objects.filter(created_at__date__gte=start_date)
        agg = (
            qs.annotate(d=TruncDate("created_at"))
              .values("d")
              .annotate(pv=Count("id"), uv=Count("operator", distinct=True), ip=Count("ip", distinct=True))
              .order_by("d")
        )
        # 构造完整 7 天序列
        date_list = [start_date + datetime.timedelta(days=i) for i in range(7)]
        m = {x["d"]: x for x in agg}
        dates = [d.strftime("%Y-%m-%d") for d in date_list]
        pv_list = [m.get(d, {}).get("pv", 0) for d in date_list]
        uv_list = [m.get(d, {}).get("uv", 0) for d in date_list]
        ip_list = [m.get(d, {}).get("ip", 0) for d in date_list]
        return drf_ok({"dates": dates, "pvList": pv_list, "uvList": uv_list, "ipList": ip_list})

    @action(detail=False, methods=["get"], url_path="visit-stats")
    def visit_stats(self, request):
        import datetime
        from django.db.models import Count
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        # 总计
        total_pv = OperLog.objects.count()
        total_uv = OperLog.objects.aggregate(c=Count("operator", distinct=True))['c'] or 0
        # 今日与昨日
        qs_today = OperLog.objects.filter(created_at__date=today)
        qs_yest = OperLog.objects.filter(created_at__date=yesterday)
        today_pv = qs_today.count()
        today_uv = qs_today.aggregate(c=Count("operator", distinct=True))['c'] or 0
        y_pv = qs_yest.count()
        y_uv = qs_yest.aggregate(c=Count("operator", distinct=True))['c'] or 0
        pv_growth = ((today_pv - y_pv) / y_pv * 100.0) if y_pv else (100.0 if today_pv > 0 else 0.0)
        uv_growth = ((today_uv - y_uv) / y_uv * 100.0) if y_uv else (100.0 if today_uv > 0 else 0.0)
        return drf_ok({
            "todayUvCount": today_uv,
            "totalUvCount": total_uv,
            "uvGrowthRate": round(uv_growth, 2),
            "todayPvCount": today_pv,
            "totalPvCount": total_pv,
            "pvGrowthRate": round(pv_growth, 2),
        })

class ConfigViewSet(viewsets.ViewSet):
    """参数配置接口

    按钮级权限映射：
    - 查询: sys:config:query -> page / list_or_create(GET) / form
    - 新增: sys:config:add   -> list_or_create(POST)
    - 编辑: sys:config:edit  -> update_or_delete(PUT)
    - 删除: sys:config:delete-> update_or_delete(DELETE)
    刷新缓存暂归入查询权限（需要看到菜单即可）。
    """

    permission_classes = [MenuPermRequired]

    def get_permissions(self):
        action = getattr(self, 'action', None)
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        required = None
        if action in ('page', 'form') or (action == 'list_or_create' and method == 'GET'):
            required = ['sys:config:query']
        elif action == 'list_or_create' and method == 'POST':
            required = ['sys:config:add']
        elif action == 'update_or_delete' and method == 'PUT':
            required = ['sys:config:edit']
        elif action == 'update_or_delete' and method == 'DELETE':
            required = ['sys:config:delete']
        elif action == 'refresh_cache':
            required = ['sys:config:query']
        setattr(self, 'required_perms', required)
        return super().get_permissions()

    @staticmethod
    def _serialize(conf: Config):
        return {
            "id": conf.id,
            "configName": conf.key,  # 简化：使用 key 作为名称
            "configKey": conf.key,
            "configValue": conf.value,
            "status": 1 if conf.status else 0,
            "remark": conf.remark,
        }

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        qs = Config.objects.all().order_by("id")
        kw = request.query_params.get("keywords")
        if kw:
            qs = qs.filter(Q(key__icontains=kw) | Q(value__icontains=kw))
        total, items, _, _ = paginate_queryset(request, qs)
        data = [self._serialize(c) for c in items]
        # write_log removed: 查询参数分页：{total} 条
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == 'get':
            items = Config.objects.all().order_by("id")
            # write_log removed: 查询参数列表：{len(items)} 条
            return drf_ok([self._serialize(c) for c in items])
        import time
        t0 = time.perf_counter()
        p = request.data.copy()
        key = p.get("configKey") or p.get("key") or p.get("configName")
        value = p.get("configValue") or p.get("value") or ""
        remark = p.get("remark") or ""
        status = p.get("status", 1)
        c = Config.objects.create(key=key or "", value=value, remark=remark, status=bool(int(status)) if isinstance(status, (str, int)) else bool(status))
        # write_log removed: 新增参数：{c.key}（ID={c.id}）
        return drf_ok(self._serialize(c), status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        try:
            c = Config.objects.get(pk=id)
        except Config.DoesNotExist:
            return drf_error("未找到参数", status=404)
        # write_log removed: 查看参数表单：{c.key}（ID={c.id}）
        return drf_ok(self._serialize(c))

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == 'put':
            first_id = ids.split(',')[0]
            try:
                c = Config.objects.get(pk=first_id)
            except Config.DoesNotExist:
                return drf_error("未找到参数", status=404)
            p = request.data.copy()
            if "configKey" in p or "key" in p or "configName" in p:
                c.key = p.get("configKey") or p.get("key") or p.get("configName") or c.key
            if "configValue" in p or "value" in p:
                c.value = p.get("configValue") or p.get("value") or c.value
            if "remark" in p:
                c.remark = p.get("remark") or c.remark
            if "status" in p:
                s = p.get("status")
                c.status = bool(int(s)) if isinstance(s, (str, int)) else bool(s)
            c.save()
            # write_log removed: 更新参数：{c.key}（ID={c.id}）
            return drf_ok(self._serialize(c))
        id_list = [i for i in ids.split(',') if i]
        Config.objects.filter(id__in=id_list).delete()
        # write_log removed: 删除参数：{ids}
        return drf_ok(status=204)

    @action(detail=False, methods=["post"], url_path="refresh-cache")
    def refresh_cache(self, request):
        # write_log removed: 刷新参数缓存
        return drf_ok({"message": "refreshed"})
