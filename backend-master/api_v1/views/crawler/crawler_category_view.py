"""爬取类目视图（CrawlerCategory）。

包含 CRUD、Seafile 时间目录列表、文件下载链接探测等接口。

私有辅助函数（仅本视图使用）：
- ``_get_config_val``：从参数配置表读取 Seafile 配置项。
- ``_resolve_site_and_repo``：从参数配置表读取 Seafile 站点与资料库 ID。
- ``_get_admin_token``：使用管理员账号获取 Seafile API Token。
- ``_build_paths`` / ``_make_urls``：根据类目与时间目录构建 Seafile 路径与外链。
"""
import re
from urllib.parse import quote

import requests
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.models import CrawlerCategory, Config
from api_v1.serializers import CrawlerCategorySerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


# ---------- 私有辅助函数 ----------

def _get_config_val(key: str) -> str:
    """从参数配置表读取指定 key 的值。"""
    try:
        obj = Config.objects.filter(key=key, status=True).first()
        return (obj.value or "").strip() if obj else ""
    except Exception:
        return ""


def _resolve_site_and_repo(cat_site=None):
    """从参数配置表读取 Seafile 站点与资料库 ID。"""
    site = _get_config_val("SEAFILE_SITE")
    repo_id = _get_config_val("SEAFILE_REPO_ID")

    if not site:
        return None, None, "未在参数配置中找到 Seafile 站点（SEAFILE_SITE），请先配置"
    if not repo_id:
        return None, None, "未在参数配置中找到 Seafile 资料库 ID（SEAFILE_REPO_ID），请先配置"

    base_site = str(site).strip()
    if not re.match(r"^https?://", base_site, re.I):
        base_site = "https://" + base_site
    return base_site, repo_id, None


def _get_admin_token(base_site: str):
    """使用管理员账号获取 Seafile API Token。

    Returns:
        tuple[str | None, str | None]: (token, error_msg)
    """
    admin_user = _get_config_val("SEAFILE_ADMIN_USER")
    admin_pass = _get_config_val("SEAFILE_ADMIN_PASSWORD")
    if not admin_user or not admin_pass:
        return None, "未配置 Seafile 管理员账号（SEAFILE_ADMIN_USER / SEAFILE_ADMIN_PASSWORD）"
    auth_url = base_site.rstrip("/") + "/api2/auth-token/"
    try:
        resp = requests.post(auth_url, json={"username": admin_user, "password": admin_pass}, timeout=10)
        if 200 <= resp.status_code < 300:
            token = resp.json().get("token")
            if token:
                return token, None
        return None, f"Seafile 管理员认证失败：{resp.status_code}"
    except Exception as exc:
        return None, f"请求 Seafile 认证失败：{exc}"


def _build_paths(cat, t):
    """根据类目对象和时间构建 ``folder, file_name, p_raw, view_path_parts``。"""
    folder = str(cat.site or "").strip("/")
    file_name = f"{cat.category_id}_{cat.site}.xlsx"
    p_raw = f"/爬虫数据/{folder}/{t}/{file_name}"
    view_path_parts = ["爬虫数据", folder, t, file_name]
    return folder, file_name, p_raw, view_path_parts


def _make_urls(base_site, repo_id, p_raw, view_path_parts):
    """返回 ``(download_url, view_url)`` 两个外链。"""
    try:
        download_url = base_site.rstrip("/") + f"/api2/repos/{quote(repo_id)}/file/?p={quote(p_raw)}"
    except Exception:
        download_url = None
    try:
        view_path = "/".join([quote(str(p)) for p in view_path_parts])
        view_url = base_site.rstrip("/") + f"/lib/{quote(repo_id)}/file/{view_path}"
    except Exception:
        view_url = None
    return download_url, view_url


# ---------- 视图类 ----------

class CrawlerCategoryViewSet(viewsets.ViewSet):
    """爬取类目的分页与 CRUD。"""

    def get_permissions(self):
        method = getattr(self.request, "method", "").upper() if hasattr(self, "request") else ""
        if method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        qs = CrawlerCategory.objects.all().order_by("-created_at", "id")
        kw = request.query_params.get("keywords") or request.query_params.get("keyword")
        if kw:
            try:
                k = str(kw).strip()
                if k:
                    qs = qs.filter(Q(name__icontains=k) | Q(category_id__icontains=k))
            except Exception:
                pass
        site_q = request.query_params.get("site") or request.query_params.get("siteName")
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
        if request.method.lower() == "get":
            qs = CrawlerCategory.objects.all().order_by("-created_at", "id")
            total, items, _, _ = paginate_queryset(request, qs)
            data = CrawlerCategorySerializer(items, many=True).data
            return drf_ok(data)
        # create
        payload = request.data or {}
        name_val = payload.get("name", "") or payload.get("categoryName", "")
        category_id_val = payload.get("category_id", "") or payload.get("categoryId", "") or ""
        site_val = payload.get("site", "") or ""
        try:
            s_clean = str(site_val or "").strip()
            c_clean = str(category_id_val or "").strip()
            if CrawlerCategory.objects.filter(site__iexact=s_clean, category_id=c_clean).exists():
                return drf_error("类目站点 类目ID 已经添加", status=400)
        except Exception:
            pass

        obj = CrawlerCategory.objects.create(
            name=name_val,
            category_id=category_id_val,
            site=site_val,
            category_type=payload.get("category_type", "") or payload.get("categoryType", ""),
            status=int(payload.get("status", 1)),
        )
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
        if request.method.lower() == "put":
            first_id = ids.split(",")[0]
            try:
                obj = CrawlerCategory.objects.get(pk=first_id)
            except CrawlerCategory.DoesNotExist:
                return drf_error("未找到类目", status=404)
            p = request.data or {}
            new_site = None
            new_catid = None
            if "site" in p:
                new_site = p.get("site") or obj.site
            if "category_id" in p or "categoryId" in p:
                new_catid = p.get("category_id") or p.get("categoryId") or obj.category_id
            try:
                if (new_site is not None or new_catid is not None):
                    s_check = str((new_site if new_site is not None else obj.site) or "").strip()
                    c_check = str((new_catid if new_catid is not None else obj.category_id) or "").strip()
                    # 排除当前对象自身
                    if CrawlerCategory.objects.filter(site__iexact=s_check, category_id=c_check).exclude(id=obj.id).exists():
                        return drf_error("类目站点 类目ID 已经添加", status=400)
            except Exception:
                pass

            if "name" in p:
                obj.name = p.get("name") or obj.name
            if "category_id" in p or "categoryId" in p:
                obj.category_id = p.get("category_id") or p.get("categoryId") or obj.category_id
            if "site" in p:
                obj.site = p.get("site") or obj.site
            if "category_type" in p or "categoryType" in p:
                obj.category_type = p.get("category_type") or p.get("categoryType") or obj.category_type
            if "status" in p:
                try:
                    obj.status = int(p.get("status"))
                except Exception:
                    pass
            obj.save()
            return drf_ok(CrawlerCategorySerializer(obj).data)
        # delete
        id_list = [i for i in ids.split(",") if i]
        CrawlerCategory.objects.filter(id__in=id_list).delete()
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

            # 使用管理员 token 访问 Seafile
            token, token_err = _get_admin_token(base_site)
            if not token:
                return drf_error(token_err or "无法获取 Seafile 管理员 token", status=502)

            try:
                auth_header = {"Authorization": f"Token {token}", "Accept": "application/json, text/plain, */*"}
                repo_url = base_site.rstrip("/") + f"/api2/repos/{quote(repo_id)}/dir/"
                folder_name = (cat.site or str(cat.category_id or "")).strip().strip("/")
                params = {"p": f"/爬虫数据/{folder_name}/"}
                resp = requests.get(repo_url, headers=auth_header, params=params, timeout=10)
            except Exception as e:
                return drf_error("请求 Seafile 失败", status=502, data={"msg": str(e)})

            if resp.status_code in (401, 403):
                return drf_error("Seafile 管理员认证失败或 token 无效", status=502)

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
                        nm = it.get("name") or it.get("path") or it.get("filename")
                        is_dir = bool(it.get("is_dir") or (it.get("type") == "dir") or it.get("isdir"))
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
            qs = CrawlerCategory.objects.all().order_by("site").values_list("site", flat=True).distinct()
            sites = [s for s in list(qs) if s]
            return drf_ok(sites)
        except Exception as e:
            return drf_error("获取站点列表失败", status=500, data={"msg": str(e)})

    @action(detail=True, methods=["get"], url_path="file", permission_classes=[IsAuthenticated])
    def file(self, request, id: str):
        try:
            t = request.query_params.get("time") or request.query_params.get("date")
            if not t:
                return drf_error("缺少 time 参数", status=400)
            try:
                cat = CrawlerCategory.objects.get(pk=id)
            except CrawlerCategory.DoesNotExist:
                return drf_error("未找到类目", status=404)

            base_site, repo_id, err = _resolve_site_and_repo(cat.site)
            if err:
                return drf_error(err, status=400)

            # 使用管理员 token 访问 Seafile
            token, token_err = _get_admin_token(base_site)
            if not token:
                return drf_error(token_err or "无法获取 Seafile 管理员 token", status=502)

            folder, file_name, p_raw, view_path_parts = _build_paths(cat, t)

            # 从 Seafile 获取文件详情
            url = base_site.rstrip("/") + f"/api2/repos/{quote(repo_id)}/file/detail/?p={quote(p_raw)}"
            headers = {"Authorization": f"Token {token}"}
            r = requests.get(url, headers=headers, timeout=5)

            if r.status_code in (401, 403):
                return drf_error("Seafile 管理员认证失败或 token 无效", status=502)

            if r.status_code == 200:
                try:
                    jr = r.json()
                except Exception:
                    jr = None
                download_url, view_url = _make_urls(base_site, repo_id, p_raw, view_path_parts)
                data = {"exists": True, "downloadUrl": download_url, "viewUrl": view_url}
                if isinstance(jr, dict):
                    data["size"] = jr.get("size")
                    data["mtime"] = jr.get("mtime") or jr.get("last_modified") or jr.get("mtime_ms")
                return drf_ok(data)
            return drf_ok({"exists": False}, status=404)
        except Exception as e:
            return drf_error(str(e), status=500)

    @action(detail=True, methods=["get"], url_path="file/check", permission_classes=[IsAuthenticated])
    def file_check(self, request, id: str):
        try:
            t = request.query_params.get("time") or request.query_params.get("date")
            if not t:
                return drf_error("缺少 time 参数", status=400)
            try:
                cat = CrawlerCategory.objects.get(pk=id)
            except CrawlerCategory.DoesNotExist:
                return drf_error("未找到类目", status=404)

            base_site, repo_id, err = _resolve_site_and_repo(cat.site)
            if err:
                return drf_error(err, status=400)

            # 使用管理员 token 访问 Seafile
            token, token_err = _get_admin_token(base_site)
            if not token:
                return drf_error(token_err or "无法获取 Seafile 管理员 token", status=502)

            folder = str(cat.site or "").strip("/")
            file_name = f"{cat.category_id}_{cat.site}.xlsx"
            p_raw = f"/爬虫数据/{folder}/{t}/{file_name}"

            # 尝试探测下载/查看 URL
            params = {"p": p_raw}
            auth_header = {"Authorization": f"Token {token}", "Accept": "application/json, text/plain, */*"}
            repo_url = base_site.rstrip("/") + f"/api2/repos/{quote(repo_id)}/file/"
            # 不跟随重定向：Seafile 可能返回 Location 指向外部 seafhttp
            try:
                r = requests.get(repo_url, headers=auth_header, params=params, stream=False, timeout=15, allow_redirects=False)
            except Exception as e:
                return drf_error("Seafile 请求失败", status=502, data={"msg": str(e)})

            # Seafile 返回重定向，使用 Location 作为下载链接
            if r.status_code in (301, 302, 303, 307, 308):
                download_url = r.headers.get("Location")
                try:
                    view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                    view_url = base_site.rstrip("/") + f"/lib/{quote(repo_id)}/file/{view_path}"
                except Exception:
                    view_url = None
                return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})

            # 200：尝试从响应体解析 URL 或 JSON
            if r.status_code == 200:
                ctype = (r.headers.get("Content-Type") or "").lower()
                body = ""
                try:
                    body = r.text or ""
                except Exception:
                    body = ""

                body_str = (body or "").strip()
                # 去除两端引号
                if len(body_str) >= 2 and ((body_str[0] == '"' and body_str[-1] == '"') or (body_str[0] == "'" and body_str[-1] == "'")):
                    body_str = body_str[1:-1].strip()

                if body_str.startswith("http://") or body_str.startswith("https://"):
                    download_url = body_str
                    try:
                        view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                        view_url = base_site.rstrip("/") + f"/lib/{quote(repo_id)}/file/{view_path}"
                    except Exception:
                        view_url = None
                    return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})

                # 若是 JSON，检查错误或内嵌 URL
                try:
                    if "application/json" in ctype:
                        try:
                            jr = r.json()
                        except Exception:
                            jr = None
                        if isinstance(jr, dict) and (jr.get("error_msg") or jr.get("detail")):
                            msg = jr.get("error_msg") or jr.get("detail") or ""
                            if "File not found" in msg or "not found" in msg.lower():
                                return drf_ok({"exists": False, "error_msg": msg})
                            return drf_error("Seafile 返回错误", status=502, data={"msg": msg})
                except Exception:
                    pass

                # 用正则提取 seafhttp 链接
                try:
                    bt = body or ""
                    m = re.search(r"https?://[\w\-\.\/:=%?&]+/(?:seafhttp|seaf)/[\w\-\.\/:=%?&]+", bt)
                    if m:
                        download_url = m.group(0).strip().strip("\"'")
                        try:
                            view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                            view_url = base_site.rstrip("/") + f"/lib/{quote(repo_id)}/file/{view_path}"
                        except Exception:
                            view_url = None
                        return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})
                except Exception:
                    pass

                # 跟随重定向再次探测
                try:
                    probe = None
                    try:
                        probe = requests.get(repo_url, headers=auth_header, params=params, timeout=20, allow_redirects=True)
                    except Exception:
                        probe = None
                    if probe is not None:
                        try:
                            final_url = getattr(probe, "url", "") or ""
                            if final_url and final_url.strip() and (final_url != repo_url) and (final_url.startswith("http://") or final_url.startswith("https://")):
                                if "/seafhttp/" in final_url or "/seaf/" in final_url:
                                    download_url = final_url
                                    try:
                                        view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                                        view_url = base_site.rstrip("/") + f"/lib/{quote(repo_id)}/file/{view_path}"
                                    except Exception:
                                        view_url = None
                                    return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})
                            try:
                                body_text = probe.text or ""
                            except Exception:
                                body_text = ""
                            if "/seafhttp/" in body_text or "/seaf/" in body_text:
                                m = re.search(r"https?://[\w\-\.\/:=%?&]+/seafhttp/[\w\-\.\/:=%?&]+", body_text)
                                if m:
                                    download_url = m.group(0)
                                    try:
                                        view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                                        view_url = base_site.rstrip("/") + f"/lib/{quote(repo_id)}/file/{view_path}"
                                    except Exception:
                                        view_url = None
                                    return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})
                        except Exception:
                            pass
                except Exception:
                    pass

                # 兜底：构造 API 下载链接
                download_url = base_site.rstrip("/") + f"/api2/repos/{quote(repo_id)}/file/?p={quote(p_raw)}"
                try:
                    view_path = "/".join([quote(p) for p in ["爬虫数据", folder, t, file_name]])
                    view_url = base_site.rstrip("/") + f"/lib/{quote(repo_id)}/file/{view_path}"
                except Exception:
                    view_url = None
                return drf_ok({"exists": True, "viewUrl": view_url, "downloadUrl": download_url})

            if r.status_code == 404:
                return drf_ok({"exists": False, "error_msg": "File not found"})
            if r.status_code in (401, 403):
                # 视为 token 异常；返回 401 触发前端要求 cloudPassword
                return drf_error("Seafile 认证失败或 token 无效", status=401)
            return drf_error("未知 Seafile 响应", status=502, data={"status_code": r.status_code})
        except Exception as e:
            return drf_error(str(e), status=500)
