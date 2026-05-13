"""爬虫日志视图（CrawlerLog）。"""
from datetime import datetime, timedelta

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

from api_v1.models import CrawlerLog
from api_v1.serializers import CrawlerLogSerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


class CrawlerLogViewSet(viewsets.ViewSet):
    """爬虫日志（开放式接口）：允许任何人提交与查询日志，用于采集/调试场景。

    - GET  /crawler/logs/page -> 分页查询，支持 keywords（匹配日志内容）、createTime 日期范围
    - GET  /crawler/logs -> 列表（非分页）
    - POST /crawler/logs -> 新增日志（接受 module, action/content, result/level, elapsed_ms,
      operator, ip, user_agent）
    """

    def get_permissions(self):
        # 对所有动作均开放（AllowAny）
        return [AllowAny()]

    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        try:
            qs = CrawlerLog.objects.all().order_by("-id")
            # 关键字仅匹配日志内容（content）
            keywords = request.query_params.get("keywords") or request.query_params.get("keyword")
            if keywords:
                qs = qs.filter(Q(content__icontains=keywords))

            # 时间范围 createTime[]=start&createTime[]=end （YYYY-MM-DD）
            date_range = request.query_params.getlist("createTime[]") or request.query_params.getlist("createTime")
            if date_range and len(date_range) >= 2 and date_range[0] and date_range[1]:
                try:
                    start = datetime.strptime(date_range[0], "%Y-%m-%d")
                    end = datetime.strptime(date_range[1], "%Y-%m-%d") + timedelta(days=1)
                    qs = qs.filter(created_at__gte=start, created_at__lt=end)
                except Exception:
                    pass

            total, items, _, _ = paginate_queryset(request, qs)
            raw = CrawlerLogSerializer(items, many=True).data
            data = [self._to_front_row(r) for r in raw]
            return drf_ok({"total": total, "list": data})
        except Exception as e:
            return drf_error("服务器内部错误", status=500, data={"msg": str(e)})

    @action(detail=False, methods=["get"], url_path="")
    def list_or_create(self, request):
        # GET 列表（非分页）
        if request.method.lower() == "get":
            qs = CrawlerLog.objects.all().order_by("-id")
            raw = CrawlerLogSerializer(qs, many=True).data
            data = [self._to_front_row(r) for r in raw]
            return drf_ok(data)

        # POST 创建日志
        p = request.data or {}
        try:
            payload = {
                "module": p.get("module") or p.get("模块") or p.get("mod") or "",
                "content": p.get("content") or p.get("action") or p.get("日志内容") or "",
                "level": (p.get("level") or p.get("result") or p.get("日志级别")) or "info",
                "elapsed_ms": int(p.get("executionTime") or p.get("elapsed_ms") or p.get("模块耗时") or 0),
                "operator": p.get("operator") or p.get("操作人") or "",
                "ip": p.get("ip") or p.get("IP") or "",
                "user_agent": p.get("user_agent") or p.get("userAgent") or "",
            }
            s = CrawlerLogSerializer(data=payload)
            s.is_valid(raise_exception=True)
            obj = s.save()
            # 兼容：若传入 created_at，则尝试更新该字段
            created_at = p.get("created_at") or p.get("createTime") or None
            if created_at:
                try:
                    fmt = "%Y-%m-%d %H:%M:%S" if (len(str(created_at)) > 10 and ":" in str(created_at)) else "%Y-%m-%d"
                    dt = datetime.strptime(str(created_at), fmt)
                    obj.created_at = dt
                    obj.save(update_fields=["created_at"])
                except Exception:
                    pass
            return drf_ok({"id": obj.id}, status=201)
        except Exception as e:
            return drf_error("创建日志失败", status=400, data={"msg": str(e)})

    @staticmethod
    def _to_front_row(r: dict) -> dict:
        """将 serializer 输出转换为前端列表所需的 camelCase 行结构。"""
        return {
            "id": r.get("id"),
            "createTime": r.get("created_at"),
            "level": r.get("level"),
            "module": r.get("module"),
            "content": r.get("content") or "",
            "executionTime": r.get("elapsed_ms"),
        }
