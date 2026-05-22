"""爬取类目视图（CrawlerCategory）。

包含分页查询、CRUD 与站点下拉接口。
Seafile 文件探测相关接口（times / file / file_check）已移除，后续按需补充。
"""
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.models import CrawlerCategory
from api_v1.serializers import CrawlerCategorySerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


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
                if new_site is not None or new_catid is not None:
                    s_check = str((new_site if new_site is not None else obj.site) or "").strip()
                    c_check = str((new_catid if new_catid is not None else obj.category_id) or "").strip()
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

    @action(detail=False, methods=["get"], url_path="sites")
    def sites(self, request):
        try:
            qs = CrawlerCategory.objects.all().order_by("site").values_list("site", flat=True).distinct()
            sites = [s for s in list(qs) if s]
            return drf_ok(sites)
        except Exception as e:
            return drf_error("获取站点列表失败", status=500, data={"msg": str(e)})
