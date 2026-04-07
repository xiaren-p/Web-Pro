from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from api_v1.models import ProductClassification
from api_v1.serializers import ProductClassificationSerializer
from api_v1.utils.responses import drf_ok, drf_error

class ProductClassificationViewSet(ModelViewSet):
    """
    产品归类管理视图
    """
    queryset = ProductClassification.objects.all().order_by('-updated_at')
    serializer_class = ProductClassificationSerializer
    # 指定 msku 为查找字段，方便通过 /api/v1/product-classification/{msku}/ 进行单条查改删
    lookup_field = 'msku'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['msku', 'classification_type']
    search_fields = ['msku', 'sku']
    ordering_fields = ['updated_at', 'created_at']

    @action(detail=False, methods=['post'], url_path='query')
    def query_by_mskus(self, request):
        """
        根据 MSKU 列表批量查询
        Request Body: ["msku1", "msku2"] 或 { "mskus": [...] }
        """
        data = request.data
        mskus = []
        
        if isinstance(data, list):
            mskus = data
        elif isinstance(data, dict):
            mskus = data.get('mskus', [])
            
        if not mskus:
            return drf_ok([])

        objs = ProductClassification.objects.filter(msku__in=mskus)
        serializer = self.get_serializer(objs, many=True)
        return drf_ok(serializer.data)

    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert(self, request):
        """
        批量设置归类
        """
        data = request.data
        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            return drf_error("数据格式错误")

        saved_items = []
        for item in items:
            msku = item.get('msku')
            sku = item.get('sku')
            c_type = item.get('classification_type')
            
            # 兼容前端传递参数名可能不一致的情况
            if not msku:
                msku = item.get('seller_sku')
            
            if not msku:
                continue
            
            msku = str(msku).strip()

            if not c_type and c_type != "":
                 # 若完全未传，跳过
                 continue

            if c_type == "":
                # 清除，如果 c_type 为空字符串，则视为删除分类
                ProductClassification.objects.filter(msku=msku).delete()
                continue
            
            # 构造更新字典
            defaults = {
                'classification_type': c_type
            }
            # 只有当 sku 有值时才更新 sku，避免覆盖为空（视业务需求而定，这里假设前端传了就覆盖，没传可以保留）
            # 或者按照原逻辑： sku 这里主要起展示作用，保持最新即可
            if sku is not None:
                defaults['sku'] = str(sku).strip()
            else:
                defaults['sku'] = ''

            obj, created = ProductClassification.objects.update_or_create(
                msku=msku,
                defaults=defaults
            )
            saved_items.append(obj)
            
        serializer = self.get_serializer(saved_items, many=True)
        return drf_ok(serializer.data, msg="操作成功")
