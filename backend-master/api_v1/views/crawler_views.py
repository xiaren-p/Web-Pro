"""爬虫采集相关视图。

模块说明：提供爬虫类目的管理、文件检测、站点/时间列表、抓取任务等与 Seafile 交互的接口。
"""

import json
import re
import requests
import traceback
import time
from urllib.parse import quote
from datetime import datetime

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.models import (
    CrawlerConf, CrawlerSellerAccount, CrawlerLog, CrawlerCategory, DictItem
)
try:
    from api_v1.models import CloudAuthToken
except ImportError:
    CloudAuthToken = None

from api_v1.serializers import (
    CrawlerConfSerializer, CrawlerSellerSerializer, CrawlerLogSerializer, CrawlerCategorySerializer
)
from api_v1.utils.responses import drf_ok, drf_error
from api_v1.utils.pagination import paginate_queryset
# write_log 调用已移除

# --- Crawler Conf (开放接口，无需认证) ---
class CrawlerConfViewSet(viewsets.ViewSet):
    """数据采集节点配置（对外开放，无需认证）

    路由：
    - GET /crawler/conf -> 列表
    - POST /crawler/conf -> 新增
    - GET /crawler/conf/<id>/form -> 获取表单数据
    - PUT /crawler/conf/<ids> -> 更新（多个 id 传入逗号，以第一个为目标）
    - DELETE /crawler/conf/<ids> -> 删除
    """

    def get_permissions(self):
        """权限策略：
        - GET 请求（列表/表单）对外开放 AllowAny
        - 写操作（POST/PUT/DELETE）需要登录 IsAuthenticated
        """
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        if method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == 'get':
            qs = CrawlerConf.objects.all().order_by("order_num", "id")
            # 支持关键字搜索，匹配服务器名称或节点
            kw = request.query_params.get('keywords') or request.query_params.get('keyword')
            if kw:
                qs = qs.filter(Q(server_name__icontains=kw) | Q(node__icontains=kw))
            # 支持两种返回格式：
            # - 若前端传入分页参数（pageNum/pageSize），返回 {total, list}
            # - 否则返回数组以匹配部分旧前端组件的期望
            total, items, _, _ = paginate_queryset(request, qs)
            data = CrawlerConfSerializer(items, many=True).data
            if request.query_params.get('pageNum') or request.query_params.get('page'):
                return drf_ok({"total": total, "list": data})
            return drf_ok(data)
        # create
        import time
        t0 = time.perf_counter()
        payload = request.data or {}
        conf = CrawlerConf.objects.create(
            server_name=payload.get('server_name', '') or payload.get('serverName', ''),
            node=payload.get('node', ''),
            ip=payload.get('ip', ''),
            status=int(payload.get('status', 1)),
            order_num=int(payload.get('order_num', 0) or payload.get('orderNum', 0)),
        )
        # logging removed: 新增节点事件
        return drf_ok(CrawlerConfSerializer(conf).data, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        import traceback
        try:
            conf = CrawlerConf.objects.get(pk=id)
            return drf_ok(CrawlerConfSerializer(conf).data)
        except CrawlerConf.DoesNotExist:
            return drf_error("未找到配置", status=404)
        except Exception as e:
            tb = traceback.format_exc()
            return drf_error("获取配置失败", status=500, data={"msg": str(e), "trace": tb})

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == 'put':
            first_id = ids.split(',')[0]
            try:
                conf = CrawlerConf.objects.get(pk=first_id)
            except CrawlerConf.DoesNotExist:
                return drf_error("未找到配置", status=404)
            p = request.data or {}
            if 'server_name' in p or 'serverName' in p:
                conf.server_name = p.get('server_name') or p.get('serverName') or conf.server_name
            if 'node' in p:
                conf.node = p.get('node') or conf.node
            if 'ip' in p:
                conf.ip = p.get('ip') or conf.ip
            if 'status' in p:
                try:
                    conf.status = int(p.get('status'))
                except Exception:
                    conf.status = 1
            if 'order_num' in p or 'orderNum' in p:
                try:
                    conf.order_num = int(p.get('order_num') or p.get('orderNum') or conf.order_num)
                except Exception:
                    pass
            conf.save()
            # logging removed: 更新节点事件
            return drf_ok(CrawlerConfSerializer(conf).data)
        # delete
        id_list = [i for i in ids.split(',') if i]
        CrawlerConf.objects.filter(id__in=id_list).delete()
        # logging removed: 删除节点事件
        return drf_ok(status=204)


class CrawlerSellerViewSet(viewsets.ViewSet):
    """卖家精灵账号配置（对外开放，无需认证）

    路由：
    - GET /crawler/seller -> 列表
    - POST /crawler/seller -> 新增
    - GET /crawler/seller/<id>/form -> 获取表单数据
    - PUT /crawler/seller/<ids> -> 更新
    - DELETE /crawler/seller/<ids> -> 删除
    """

    def get_permissions(self):
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        if method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == 'get':
            qs = CrawlerSellerAccount.objects.all().order_by("order_num", "id")
            kw = request.query_params.get('keywords') or request.query_params.get('keyword')
            if kw:
                try:
                    qs = qs.filter(username__icontains=str(kw).strip())
                except Exception:
                    pass
            total, items, _, _ = paginate_queryset(request, qs)
            data = CrawlerSellerSerializer(items, many=True).data
            if request.query_params.get('pageNum') or request.query_params.get('page'):
                return drf_ok({"total": total, "list": data})
            return drf_ok(data)

        # create
        import time
        t0 = time.perf_counter()
        payload = request.data or {}
        try:
            obj = CrawlerSellerAccount.objects.create(
                username=payload.get('username', '') or payload.get('userName', ''),
                password=payload.get('password', '') or payload.get('pwd', ''),
                status=int(payload.get('status', 1)),
                order_num=int(payload.get('order_num', 0) or payload.get('orderNum', 0)),
            )
            # logging removed: 新增卖家账号
            return drf_ok(CrawlerSellerSerializer(obj).data, status=201)
        except Exception as e:
            return drf_error('创建卖家账号失败', status=400, data={'msg': str(e)})

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        try:
            obj = CrawlerSellerAccount.objects.get(pk=id)
        except Exception:
            return drf_error("未找到配置", status=404)
        return drf_ok(CrawlerSellerSerializer(obj).data)

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == 'put':
            first_id = ids.split(',')[0]
            try:
                conf = CrawlerSellerAccount.objects.get(pk=first_id)
            except Exception:
                return drf_error("未找到配置", status=404)
            p = request.data or {}
            if 'username' in p or 'userName' in p:
                conf.username = p.get('username') or p.get('userName') or conf.username
            if 'password' in p or 'pwd' in p:
                conf.password = p.get('password') or p.get('pwd') or conf.password
            if 'status' in p:
                try:
                    conf.status = int(p.get('status'))
                except Exception:
                    conf.status = 1
            if 'order_num' in p or 'orderNum' in p:
                try:
                    conf.order_num = int(p.get('order_num') or p.get('orderNum') or conf.order_num)
                except Exception:
                    pass
            conf.save()
            # logging removed: 更新卖家账号
            return drf_ok(CrawlerSellerSerializer(conf).data)

        id_list = [i for i in ids.split(',') if i]
        CrawlerSellerAccount.objects.filter(id__in=id_list).delete()
        # logging removed: 删除卖家账号
        return drf_ok(status=204)


class CrawlerLogViewSet(viewsets.ViewSet):
    """爬虫日志（开放式接口）：允许任何人提交与查询日志，用于采集/调试场景。

    - GET  /crawler/logs/page -> 分页查询，支持 keywords（匹配日志内容）、createTime 日期范围
    - GET  /crawler/logs -> 列表（非分页）
    - POST /crawler/logs -> 新增日志（接受 module, action/content, result/level, elapsed_ms, operator, ip, user_agent）
    """

    def get_permissions(self):
        # 对所有动作均开放（AllowAny）
        return [AllowAny()]

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        try:
            qs = CrawlerLog.objects.all().order_by("-id")
            # 关键字仅匹配日志内容（action）
            keywords = request.query_params.get('keywords') or request.query_params.get('keyword')
            if keywords:
                qs = qs.filter(Q(content__icontains=keywords))

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
            raw = CrawlerLogSerializer(items, many=True).data
            data = []
            for r in raw:
                data.append({
                    'id': r.get('id'),
                    'createTime': r.get('created_at'),
                    'level': r.get('level'),
                    'module': r.get('module'),
                    'content': r.get('content') or '',
                    'executionTime': r.get('elapsed_ms'),
                })
            return drf_ok({'total': total, 'list': data})
        except Exception as e:
            return drf_error('服务器内部错误', status=500, data={'msg': str(e)})

    @action(detail=False, methods=["get"], url_path="")
    def list_or_create(self, request):
        # GET 列表（非分页）
        if request.method.lower() == 'get':
            qs = CrawlerLog.objects.all().order_by('-id')
            raw = CrawlerLogSerializer(qs, many=True).data
            data = []
            for r in raw:
                data.append({
                    'id': r.get('id'),
                    'createTime': r.get('created_at'),
                    'level': r.get('level'),
                    'module': r.get('module'),
                    'content': r.get('content') or '',
                    'executionTime': r.get('elapsed_ms'),
                })
            return drf_ok(data)

        # POST 创建日志
        import time
        t0 = time.perf_counter()
        p = request.data or {}
        try:
            payload = {
                'module': p.get('module') or p.get('模块') or p.get('mod') or '',
                'content': p.get('content') or p.get('action') or p.get('日志内容') or '',
                'level': (p.get('level') or p.get('result') or p.get('日志级别')) or 'info',
                'elapsed_ms': int(p.get('executionTime') or p.get('elapsed_ms') or p.get('模块耗时') or 0),
                'operator': p.get('operator') or p.get('操作人') or '',
                'ip': p.get('ip') or p.get('IP') or '',
                'user_agent': p.get('user_agent') or p.get('userAgent') or '',
            }
            s = CrawlerLogSerializer(data=payload)
            s.is_valid(raise_exception=True)
            obj = s.save()
            # 兼容：若传入 created_at，则尝试更新该字段
            created_at = p.get('created_at') or p.get('createTime') or None
            if created_at:
                try:
                    from datetime import datetime
                    fmt = '%Y-%m-%d %H:%M:%S' if (len(str(created_at)) > 10 and ':' in str(created_at)) else '%Y-%m-%d'
                    dt = datetime.strptime(str(created_at), fmt)
                    obj.created_at = dt
                    obj.save(update_fields=['created_at'])
                except Exception:
                    pass
            # logging removed: 新增爬虫日志
            return drf_ok({'id': obj.id}, status=201)
        except Exception as e:
            # logging removed: 新增爬虫日志失败
            return drf_error('创建日志失败', status=400, data={'msg': str(e)})


# --- Using helper functions ---
def _extract_cloud_items():
    try:
        return list(DictItem.objects.filter(dict_type__code__in=["cloud_type", "clooud_type"], status=True))
    except Exception:
        return []


def _resolve_site_and_repo(cat_site=None):
    items = _extract_cloud_items()
    site = None
    repo_id = None
    try:
        if items:
            # 首先尝试从 label/value 中找到 site
            for it in items:
                try:
                    lab = (it.label or "").lower()
                    val = (it.value or "").strip()
                except Exception:
                    continue
                if not site and ("site" in lab or "站" in lab or val.startswith("http")):
                    site = val
            # 若未找到 site，尝试解析第一个 value 为 JSON
            if (not site) and items[0] and items[0].value:
                try:
                    j = json.loads(items[0].value)
                    site = site or j.get("site") or j.get("url") or j.get("host") or j.get("endpoint")
                except Exception:
                    pass

            # 定位 repo_id：优先精确 label
            exact_labels = {"资料库id", "资料库 id", "资料库ID", "repo id", "repoid", "repository id"}
            for it in items:
                try:
                    lab = (it.label or "").strip()
                    val = (it.value or "").strip()
                except Exception:
                    continue
                if lab in exact_labels:
                    repo_id = val
                    break
            # 若仍未找到，尝试匹配与 cat_site 相同的 label/value
            if not repo_id and cat_site:
                for it in items:
                    try:
                        lab = (it.label or "").strip()
                        val = (it.value or "").strip()
                    except Exception:
                        continue
                    if lab == str(cat_site).strip() or val == str(cat_site).strip():
                        repo_id = val
                        break
            # 解析 JSON 中的 repo 字段
            if not repo_id:
                for it in items:
                    try:
                        v = (it.value or "").strip()
                        j = json.loads(v)
                        for k in ("repo", "repo_id", "repoid", "repository", "repository_id"):
                            if j.get(k):
                                repo_id = str(j.get(k))
                                break
                        if repo_id:
                            break
                    except Exception:
                        continue
            # fallback: 若仅一项且 value 看起来不像 URL，则使用其 value
            if not repo_id and len(items) == 1:
                try:
                    v = (items[0].value or "").strip()
                    if v and not re.match(r"^https?://", v, re.I):
                        repo_id = v
                except Exception:
                    pass
    except Exception:
        pass

    if not site:
        return None, None, "未在字典中配置 Seafile 站点 (cloud_type)，请先配置 site"
    if not repo_id:
        return None, None, "未在字典中定位到资料库 ID (repo id)，请检查 cloud_type 字典项"

    base_site = str(site).strip()
    if not re.match(r"^https?://", base_site, re.I):
        base_site = "https://" + base_site
    return base_site, repo_id, None


def _build_paths(cat, t):
    """根据类目对象和时间构建 folder, file_name, p_raw, view_path_parts"""
    folder = str(cat.site or '').strip('/'
                   )
    file_name = f"{cat.category_id}_{cat.site}.xlsx"
    p_raw = f"/爬虫数据/{folder}/{t}/{file_name}"
    view_path_parts = ["爬虫数据", folder, t, file_name]
    return folder, file_name, p_raw, view_path_parts


def _make_urls(base_site, repo_id, p_raw, view_path_parts):
    """返回 (download_url, view_url) 两个外链"""
    try:
        download_url = base_site.rstrip('/') + f"/api2/repos/{quote(repo_id)}/file/?p={quote(p_raw)}"
    except Exception:
        download_url = None
    try:
        view_path = "/".join([quote(str(p)) for p in view_path_parts])
        view_url = base_site.rstrip('/') + f"/lib/{quote(repo_id)}/file/{view_path}"
    except Exception:
        view_url = None
    return download_url, view_url


class CrawlerCategoryViewSet(viewsets.ViewSet):
    """爬取类目的分页与 CRUD"""

    def get_permissions(self):
        method = getattr(self.request, 'method', '').upper() if hasattr(self, 'request') else ''
        if method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        qs = CrawlerCategory.objects.all().order_by("-created_at", "id")
        kw = request.query_params.get('keywords') or request.query_params.get('keyword')
        if kw:
            try:
                k = str(kw).strip()
                if k:
                    qs = qs.filter(Q(name__icontains=k) | Q(category_id__icontains=k))
            except Exception:
                pass
        site_q = request.query_params.get('site') or request.query_params.get('siteName')
        if site_q:
            try:
                s = str(site_q).strip()
                if s:
                    qs = qs.filter(site__iexact=s)
            except Exception:
                pass
        total, items, _, _ = paginate_queryset(request, qs)
        data = CrawlerCategorySerializer(items, many=True).data
        return drf_ok({"total": total, "list": data})

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        if request.method.lower() == 'get':
            qs = CrawlerCategory.objects.all().order_by("-created_at", "id")
            total, items, _, _ = paginate_queryset(request, qs)
            data = CrawlerCategorySerializer(items, many=True).data
            return drf_ok(data)
        # create
        payload = request.data or {}
        name_val = payload.get('name', '') or payload.get('categoryName', '')
        category_id_val = payload.get('category_id', '') or payload.get('categoryId', '') or ''
        site_val = payload.get('site', '') or ''
        try:
            s_clean = str(site_val or '').strip()
            c_clean = str(category_id_val or '').strip()
            if CrawlerCategory.objects.filter(site__iexact=s_clean, category_id=c_clean).exists():
                return drf_error("类目站点 类目ID 已经添加", status=400)
        except Exception:
            pass

        obj = CrawlerCategory.objects.create(
            name=name_val,
            category_id=category_id_val,
            site=site_val,
            category_type=payload.get('category_type', '') or payload.get('categoryType', ''),
            status=int(payload.get('status', 1)),
        )
        # logging removed: 新增类目
        return drf_ok(CrawlerCategorySerializer(obj).data, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        try:
            obj = CrawlerCategory.objects.get(pk=id)
        except CrawlerCategory.DoesNotExist:
            return drf_error("未找到类目", status=404)
        return drf_ok(CrawlerCategorySerializer(obj).data)
    
    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        if request.method.lower() == 'put':
            first_id = ids.split(',')[0]
            try:
                obj = CrawlerCategory.objects.get(pk=first_id)
            except CrawlerCategory.DoesNotExist:
                return drf_error("未找到类目", status=404)
            p = request.data or {}
            new_site = None
            new_catid = None
            if 'site' in p:
                new_site = p.get('site') or obj.site
            if 'category_id' in p or 'categoryId' in p:
                new_catid = p.get('category_id') or p.get('categoryId') or obj.category_id
            try:
                if (new_site is not None or new_catid is not None):
                    s_check = str((new_site if new_site is not None else obj.site) or '').strip()

                    c_check = str((new_catid if new_catid is not None else obj.category_id) or '').strip()
                    # 排除当前对象自身
                    if CrawlerCategory.objects.filter(site__iexact=s_check, category_id=c_check).exclude(id=obj.id).exists():
                        return drf_error("类目站点 类目ID 已经添加", status=400)
            except Exception:
                pass

            if 'name' in p:
                obj.name = p.get('name') or obj.name
            if 'category_id' in p or 'categoryId' in p:
                obj.category_id = p.get('category_id') or p.get('categoryId') or obj.category_id
            if 'site' in p:
                obj.site = p.get('site') or obj.site
            if 'category_type' in p or 'categoryType' in p:
                obj.category_type = p.get('category_type') or p.get('categoryType') or obj.category_type
            if 'status' in p:
                try:
                    obj.status = int(p.get('status'))
                except Exception:
                    pass
            obj.save()
            # logging removed: 更新类目
            return drf_ok(CrawlerCategorySerializer(obj).data)
        # delete
        id_list = [i for i in ids.split(',') if i]
        CrawlerCategory.objects.filter(id__in=id_list).delete()
        # logging removed: 删除类目
        return drf_ok(status=204)

    @action(detail=True, methods=["get"], url_path="times", permission_classes=[IsAuthenticated])
    def times(self, request, id: str):
        try:
            try:
                cat = CrawlerCategory.objects.get(pk=id)
            except CrawlerCategory.DoesNotExist:
                return drf_error("未找到类目", status=404)

            # 解析 Seafile site 与 repo_id
            base_site, repo_id, err = _resolve_site_and_repo(cat.site)
            if err:
                return drf_error(err, status=400)

            # 获取当前用户缓存的 token
            try:
                from api_v1.utils.seafile import get_cached_token, invalidate_user_token
            except Exception:
                get_cached_token = None
                invalidate_user_token = None

            token = None
            if get_cached_token:
                try:
                    token = get_cached_token(request.user, base_site)
                except Exception:
                    token = None

            if not token:
                return drf_error("未找到缓存的 Seafile token，请提供 cloudPassword 刷新缓存", status=401, data={"needCloudPassword": True})

            try:
                auth_header = {"Authorization": f"Token {token}", "Accept": "application/json, text/plain, */*"}
                repo_url = base_site.rstrip('/') + f"/api2/repos/{quote(repo_id)}/dir/"
                folder_name = (cat.site or str(cat.category_id or "")).strip().strip('/')
                params = {"p": f"/爬虫数据/{folder_name}/"}
                resp = requests.get(repo_url, headers=auth_header, params=params, timeout=10)
            except Exception as e:
                return drf_error("请求 Seafile 失败", status=502, data={"msg": str(e)})

            if resp.status_code in (401, 403):
                 if invalidate_user_token:
                     invalidate_user_token(request.user, base_site)
                 return drf_error("Seafile 认证失败或 token 无效", status=401)
            
            if not (200 <= resp.status_code < 300):
                 return drf_error(f"Seafile 返回错误: {resp.status_code}", status=502)

            try:
                jr = resp.json()
            except Exception:
                jr = None

            names = []
            if isinstance(jr, list):
                for it in jr:
                    nm = None
                    if isinstance(it, dict):
                        nm = it.get('name') or it.get('path') or it.get('filename')
                        is_dir = bool(it.get('is_dir') or (it.get('type') == 'dir') or it.get('isdir') )
                    else:
                        nm = str(it)
                        is_dir = False
                    if nm and is_dir:
                        if re.match(r"^\d{6,8}$", str(nm)):
                            names.append(str(nm))
            uniq = sorted(list(set(names)), reverse=True)
            latest = uniq[:3]
            data = {"list": [{"index": i + 1, "name": n} for i, n in enumerate(latest)], "all": uniq}
            return drf_ok(data)
        except Exception as e:
            return drf_error("服务器内部错误", status=500, data={"msg": str(e)})

    @action(detail=False, methods=["get"], url_path="sites")
    def sites(self, request):
        try:
            qs = CrawlerCategory.objects.all().order_by('site').values_list('site', flat=True).distinct()
            sites = [s for s in list(qs) if s]
            return drf_ok(sites)
        except Exception as e:
            return drf_error('获取站点列表失败', status=500, data={'msg': str(e)})

    @action(detail=True, methods=["get"], url_path="file", permission_classes=[IsAuthenticated])
    def file(self, request, id: str):
        try:
            t = request.query_params.get('time') or request.query_params.get('date')
            if not t:
                return drf_error("缺少 time 参数", status=400)
            try:
                cat = CrawlerCategory.objects.get(pk=id)
            except CrawlerCategory.DoesNotExist:
                return drf_error("未找到类目", status=404)

            base_site, repo_id, err = _resolve_site_and_repo(cat.site)
            if err:
                return drf_error(err, status=400)

            try:
                from api_v1.utils.seafile import get_cached_token, invalidate_user_token
            except Exception:
                get_cached_token = None
                invalidate_user_token = None

            token = None
            if get_cached_token:
                try:
                    token = get_cached_token(request.user, base_site)
                except Exception:
                    token = None

            if not token:
                return drf_error("未找到 Seafile token", status=401)

            folder, file_name, p_raw, view_path_parts = _build_paths(cat, t)

            # get file detail from Seafile
            url = base_site.rstrip('/') + f"/api2/repos/{quote(repo_id)}/file/detail/?p={quote(p_raw)}"
            headers = {"Authorization": f"Token {token}"}
            r = requests.get(url, headers=headers, timeout=5)

            if r.status_code in (401, 403):
                 if invalidate_user_token:
                     invalidate_user_token(request.user, base_site)
                 return drf_error("Seafile 认证失败或 token 无效", status=401)

            if r.status_code == 200:
                try:
                    jr = r.json()
                except Exception:
                    jr = None
                download_url, view_url = _make_urls(base_site, repo_id, p_raw, view_path_parts)
                data = {"exists": True, "downloadUrl": download_url, "viewUrl": view_url}
                if isinstance(jr, dict):
                    data['size'] = jr.get('size')
                    data['mtime'] = jr.get('mtime') or jr.get('last_modified') or jr.get('mtime_ms')
                return drf_ok(data)
            return drf_ok({"exists": False}, status=404)
        except Exception as e:
            return drf_error(str(e), status=500)

    @action(detail=True, methods=["get"], url_path="file/check", permission_classes=[IsAuthenticated])
    def file_check(self, request, id: str):
        try:
            t = request.query_params.get('time') or request.query_params.get('date')
            if not t:
                return drf_error("缺少 time 参数", status=400)
            try:
                cat = CrawlerCategory.objects.get(pk=id)
            except CrawlerCategory.DoesNotExist:
                return drf_error("未找到类目", status=404)

            base_site, repo_id, err = _resolve_site_and_repo(cat.site)
            if err:
                return drf_error(err, status=400)

            try:
                from api_v1.utils.seafile import get_cached_token
            except Exception:
                get_cached_token = None
            
            token = None
            if get_cached_token:
                token = get_cached_token(request.user, base_site)
            
            if not token:
                 return drf_error("未找到 Seafile token", status=401)
            
            folder = str(cat.site or '').strip('/')
            file_name = f"{cat.category_id}_{cat.site}.xlsx"
            p_raw = f"/爬虫数据/{folder}/{t}/{file_name}"
            
            # check file info and try to probe for final download/view URLs
            params = {"p": p_raw}
            auth_header = {"Authorization": f"Token {token}", "Accept": "application/json, text/plain, */*"}
            repo_url = base_site.rstrip('/') + f"/api2/repos/{quote(repo_id)}/file/"
            # Do not follow redirects initially; Seafile may return Location header pointing to external seafhttp URL
            try:
                r = requests.get(repo_url, headers=auth_header, params=params, stream=False, timeout=15, allow_redirects=False)
            except Exception as e:
                # logging removed: Seafile file_check 请求失败
                return drf_error('Seafile 请求失败', status=502, data={'msg': str(e)})

            # If Seafile returns a redirect, use Location as downloadUrl
            if r.status_code in (301, 302, 303, 307, 308):
                download_url = r.headers.get('Location')
                try:
                    view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                    view_url = base_site.rstrip('/') + f"/lib/{quote(repo_id)}/file/{view_path}"
                except Exception:
                    view_url = None
                return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})

            # If 200, try to parse body for URL or JSON containing URL
            if r.status_code == 200:
                ctype = (r.headers.get('Content-Type') or '').lower()
                body = ''
                try:
                    body = r.text or ''
                except Exception:
                    body = ''

                body_str = (body or '').strip()
                # strip surrounding quotes
                if len(body_str) >= 2 and ((body_str[0] == '"' and body_str[-1] == '"') or (body_str[0] == "'" and body_str[-1] == "'")):
                    body_str = body_str[1:-1].strip()

                if body_str.startswith('http://') or body_str.startswith('https://'):
                    download_url = body_str
                    try:
                        view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                        view_url = base_site.rstrip('/') + f"/lib/{quote(repo_id)}/file/{view_path}"
                    except Exception:
                        view_url = None
                    return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})

                # If JSON, check for error or embedded URL
                try:
                    if 'application/json' in ctype:
                        try:
                            jr = r.json()
                        except Exception:
                            jr = None
                        if isinstance(jr, dict) and (jr.get('error_msg') or jr.get('detail')):
                            msg = jr.get('error_msg') or jr.get('detail') or ''
                            if 'File not found' in msg or 'not found' in msg.lower():
                                return drf_ok({'exists': False, 'error_msg': msg})
                            return drf_error(f"Seafile 返回错误", status=502, data={'msg': msg})
                except Exception:
                    pass

                # Try to extract seafhttp link via regex
                try:
                    bt = body or ''
                    m = re.search(r"https?://[\w\-\.\/:=%?&]+/(?:seafhttp|seaf)/[\w\-\.\/:=%?&]+", bt)
                    if m:
                        download_url = m.group(0).strip().strip('"\'')
                        try:
                            view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                            view_url = base_site.rstrip('/') + f"/lib/{quote(repo_id)}/file/{view_path}"
                        except Exception:
                            view_url = None
                        return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})
                except Exception:
                    pass

                # Probe with allow_redirects=True to catch final URL
                try:
                    probe = None
                    try:
                        probe = requests.get(repo_url, headers=auth_header, params=params, timeout=20, allow_redirects=True)
                    except Exception:
                        probe = None
                    if probe is not None:
                        try:
                            final_url = getattr(probe, 'url', '') or ''
                            if final_url and final_url.strip() and (final_url != repo_url) and (final_url.startswith('http://') or final_url.startswith('https://')):
                                if '/seafhttp/' in final_url or '/seaf/' in final_url:
                                    download_url = final_url
                                    try:
                                        view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                                        view_url = base_site.rstrip('/') + f"/lib/{quote(repo_id)}/file/{view_path}"
                                    except Exception:
                                        view_url = None
                                    return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})
                            try:
                                body_text = probe.text or ''
                            except Exception:
                                body_text = ''
                            if '/seafhttp/' in body_text or '/seaf/' in body_text:
                                m = re.search(r"https?://[\w\-\.\/:=%?&]+/seafhttp/[\w\-\.\/:=%?&]+", body_text)
                                if m:
                                    download_url = m.group(0)
                                    try:
                                        view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                                        view_url = base_site.rstrip('/') + f"/lib/{quote(repo_id)}/file/{view_path}"
                                    except Exception:
                                        view_url = None
                                    return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})
                        except Exception:
                            pass
                except Exception:
                    pass

                # Fallback: construct API download URL
                download_url = base_site.rstrip('/') + f"/api2/repos/{quote(repo_id)}/file/?p={quote(p_raw)}"
                try:
                    view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                    view_url = base_site.rstrip('/') + f"/lib/{quote(repo_id)}/file/{view_path}"
                except Exception:
                    view_url = None
                return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})

            if r.status_code == 404:
                return drf_ok({"exists": False, "error_msg": "File not found"})
            if r.status_code in (401, 403):
                # treat as token issue; return 401 to let frontend ask for cloudPassword
                return drf_error("Seafile 认证失败或 token 无效", status=401)
            return drf_error('未知 Seafile 响应', status=502, data={'status_code': r.status_code})
        except Exception as e:
            return drf_error(str(e), status=500)
