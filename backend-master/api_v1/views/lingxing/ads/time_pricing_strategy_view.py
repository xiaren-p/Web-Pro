"""分时调价策略视图（LxTimePricingStrategy）。"""
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile
from api_v1.models.lingxing.ads.lx_time_pricing_strategy import LxTimePricingStrategy
from api_v1.models.lingxing.basic.lx_user import LxUser
from api_v1.models.lingxing.sales.listing.lx_product_info import LxProductInfo
from api_v1.serializers.lingxing.ads_time_pricing_strategy_serializer import LxTimePricingStrategySerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


class TimePricingStrategyViewSet(viewsets.ViewSet):
    """分时调价策略 CRUD（需要登录）。

    路由：
    - GET  /ads/time-pricing-strategy        → 分页列表（支持 keyword / status 筛选）
    - POST /ads/time-pricing-strategy        → 新增策略
    - GET  /ads/time-pricing-strategy/<id>/form → 获取单条表单数据
    - PUT  /ads/time-pricing-strategy/<ids>  → 更新（多 id 逗号分隔，以第一个为目标）
    - DELETE /ads/time-pricing-strategy/<ids> → 删除
    """

    permission_classes = [IsAuthenticated]

    # ============================================================
    # 下拉选项接口
    # ============================================================

    @action(detail=False, methods=["get"], url_path="shops")
    def shops(self, request):
        """获取适用店铺选项（LxAdsProfile，profile_id 为值，name 为展示名）。"""
        qs = LxAdsProfile.objects.filter(status=1).values("profile_id", "name", "country_code")
        data = [
            {
                "value": item["profile_id"],
                "label": f"{item['name']}（{item['country_code']}）",
            }
            for item in qs
        ]
        return drf_ok(data)

    @action(detail=False, methods=["get"], url_path="managers")
    def managers(self, request):
        """获取负责人选项（LxUser，uid 为值，realname/username 为展示名）。"""
        qs = LxUser.objects.filter(status=1).values("uid", "realname", "username")
        data = [
            {
                "value": item["uid"],
                "label": item["realname"] or item["username"] or f"用户{item['uid']}",
            }
            for item in qs
        ]
        return drf_ok(data)

    @action(detail=False, methods=["get"], url_path="assorts")
    def assorts(self, request):
        """获取归类选项（LxProductInfo.assort 去重）。"""
        values = (
            LxProductInfo.objects
            .exclude(assort__isnull=True)
            .exclude(assort="")
            .values_list("assort", flat=True)
            .distinct()
            .order_by("assort")
        )
        data = [{"value": v, "label": v} for v in values]
        return drf_ok(data)

    @action(detail=False, methods=["get"], url_path="labels")
    def labels(self, request):
        """获取标签选项（LxProductInfo.label 去重）。"""
        values = (
            LxProductInfo.objects
            .exclude(label__isnull=True)
            .exclude(label="")
            .values_list("label", flat=True)
            .distinct()
            .order_by("label")
        )
        data = [{"value": v, "label": v} for v in values]
        return drf_ok(data)

    # ============================================================
    # CRUD
    # ============================================================

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        """列表查询 / 新增策略。"""
        if request.method.lower() == "get":
            qs = LxTimePricingStrategy.objects.all()

            # 关键字搜索：模板名称
            kw = request.query_params.get("keyword") or request.query_params.get("keywords")
            if kw:
                qs = qs.filter(Q(name__icontains=kw))

            # 状态筛选
            status = request.query_params.get("status")
            if status is not None and status != "":
                qs = qs.filter(status=int(status))

            # 分时模式筛选
            time_mode = request.query_params.get("timeMode")
            if time_mode:
                qs = qs.filter(time_mode=time_mode)

            total, items, page_num, page_size = paginate_queryset(request, qs)
            data = LxTimePricingStrategySerializer(items, many=True).data
            return drf_ok({
                "total": total,
                "list": data,
                "pageNum": page_num,
                "pageSize": page_size,
            })

        # 新增
        ser = LxTimePricingStrategySerializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            return drf_error("参数错误", status=400, data={"errors": ser.errors})
        obj = ser.save()
        return drf_ok(LxTimePricingStrategySerializer(obj).data, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)/form")
    def form(self, request, id: str):
        """获取单条策略表单数据。"""
        try:
            obj = LxTimePricingStrategy.objects.get(pk=id)
            return drf_ok(LxTimePricingStrategySerializer(obj).data)
        except LxTimePricingStrategy.DoesNotExist:
            return drf_error("未找到该策略", status=404)

    @action(detail=False, methods=["put", "delete"], url_path=r"(?P<ids>[^/]+)")
    def update_or_delete(self, request, ids: str):
        """更新或删除策略。"""
        if request.method.lower() == "put":
            first_id = ids.split(",")[0]
            try:
                obj = LxTimePricingStrategy.objects.get(pk=first_id)
            except LxTimePricingStrategy.DoesNotExist:
                return drf_error("未找到该策略", status=404)

            ser = LxTimePricingStrategySerializer(obj, data=request.data, partial=True)
            if not ser.is_valid():
                return drf_error("参数错误", status=400, data={"errors": ser.errors})
            obj = ser.save()
            return drf_ok(LxTimePricingStrategySerializer(obj).data)

        # 删除
        id_list = [i for i in ids.split(",") if i]
        LxTimePricingStrategy.objects.filter(id__in=id_list).delete()
        return drf_ok(status=204)
