from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from api_v1.models import SolarTermTag
from api_v1.serializers import SolarTermTagSerializer
from api_v1.utils.responses import drf_ok, drf_error

class SolarTermTagViewSet(ModelViewSet):
    """
    节气标签管理视图
    支持标准的 CRUD 以及基于 ASIN 的批量查询
    """
    queryset = SolarTermTag.objects.all().order_by('-updated_at')
    serializer_class = SolarTermTagSerializer
    # 默认 lookup_field 为 pk (id)，如需通过 asin 操作单个资源，可使用 query 参数或自定义 action

    @action(detail=False, methods=['post'], url_path='query')
    def query_by_asins(self, request):
        """
        根据 ASIN 列表批量查询
        Request Body: ["B01XXXXX", "B02XXXXX"]  (直接传列表) 或 { "asins": [...] }
        Response: [ { "asin": "...", "tags": [...] }, ... ]
        """
        data = request.data
        asins = []
        
        if isinstance(data, list):
            asins = data
        elif isinstance(data, dict):
            asins = data.get('asins', [])
            
        if not asins:
            return drf_ok([])

        # 查询存在的记录
        objs = SolarTermTag.objects.filter(asin__in=asins)
        
        # 构造返回结果 (只返回 asin 和 tags，或者直接返回序列化整个对象)
        # 用户要求: "列表 >> 字典 两个键值 asin 和 标签列表"
        # 序列化器已经包含 asin 和 tags
        serializer = self.get_serializer(objs, many=True)
        
        # 为了方便前端匹配，可以构造一个 Map，或者直接返回 List
        # 这里直接返回 List，包含所有字段
        return drf_ok(serializer.data)

    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert(self, request):
        """
        创建或更新单个/批量 ASIN 标签
        Request Body: 
          Single: { "asin": "...", "tags": ["tag1", ...] }
          Batch:  [ { "asin": "...", "tags": [...] }, ... ]
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
            asin = item.get('asin')
            tags = item.get('tags')
            
            if not asin:
                continue
            if tags is None:
                tags = []
            
            # update_or_create
            obj, created = SolarTermTag.objects.update_or_create(
                asin=asin,
                defaults={'tags': tags}
            )
            saved_items.append(obj)
            
        serializer = self.get_serializer(saved_items, many=True)
        return drf_ok(serializer.data, msg="操作成功")
