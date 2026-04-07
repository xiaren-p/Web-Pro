from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from api_v1.utils.responses import drf_ok, drf_error
from api_v1.models import SalesProductListing, SolarTermTag, ProductClassification
from api_v1.serializers import SalesProductListingSerializer
from django.db.models import Q, IntegerField, FloatField, Subquery, OuterRef
from django.db.models.functions import Cast, Coalesce
import uuid

class SalesProductListingViewSet(ViewSet):
    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        """
        获取 Listing 列表分页数据
        """
        params = request.query_params
        page_num = int(params.get('pageNum', 1))
        page_size = int(params.get('pageSize', 50))
        
        keyword = params.get('keywords', '')
        search_type = params.get('searchType', '')

        # 辅助函数：健壮地获取列表参数（支持 key, key[], 以及逗号分隔字符串）
        def get_param_list(key):
            raw = params.getlist(key) or params.getlist(f"{key}[]")
            result = []
            for item in raw:
                # 某些前端框架可能将数组序列化为逗号分隔字符串
                if ',' in item:
                    result.extend([x.strip() for x in item.split(',') if x.strip()])
                else:
                    if item.strip():
                        result.append(item.strip())
            return result
        
        # 基础查询
        queryset = SalesProductListing.objects.all().order_by('-listing_update_date', '-id')

        # Annotate DB classification：先尝试以 msku 匹配（seller_sku），若无则以 sku 匹配（local_sku）
        msku_sub = Subquery(
            ProductClassification.objects.filter(msku=OuterRef('seller_sku')).values_list('classification_type', flat=True)[:1]
        )
        sku_sub = Subquery(
            ProductClassification.objects.filter(sku=OuterRef('local_sku')).values_list('classification_type', flat=True)[:1]
        )

        queryset = queryset.annotate(
            db_classification=Coalesce(msku_sub, sku_sub)
        )
        
        # 1. 字段筛选：国家 (marketplace)
        countries = get_param_list('country')
        if countries:
            # 过滤掉 '' 和特殊值 if any
            countries = [c for c in countries if c != '__ALL__']
            if countries:
                queryset = queryset.filter(marketplace__in=countries)

        # 2. 字段筛选：店铺 (sid)
        shop_ids = get_param_list('shopId')
        if shop_ids:
            shop_ids = [s for s in shop_ids if s != '__ALL__']
            if shop_ids:
                queryset = queryset.filter(sid__in=shop_ids)

        # 3. 字段筛选：Category (基于 ProductClassification 数据库字段)
        # 前端传参: categoryType[] = ['饰品', '普货', '正常服装', '情趣服装', '其他', '无']
        # 说明：增加 '无' 选项用于匹配未归类项目；其它选项使用字符串模糊匹配（icontains）。
        cat_types = get_param_list('categoryType')
        if cat_types:
            cat_types = [c for c in cat_types if c != '__ALL__']
            if cat_types:
                cat_q = Q()
                for ct in cat_types:
                    if ct == '无':
                        # db_classification 为空或 NULL
                        cat_q |= Q(db_classification__isnull=True) | Q(db_classification__exact='')
                    else:
                        # 使用字符串匹配以支持模糊分类名匹配
                        cat_q |= Q(db_classification__icontains=ct)
                queryset = queryset.filter(cat_q)

        # 4. 字段筛选：配对状态 (local_sku, fnsku)
        # paired: local_sku 和 fnsku 都有值
        # unpaired: local_sku 或 fnsku 为空
        pair_status = get_param_list('pairStatus')
        if pair_status:
            pair_status = [p for p in pair_status if p != '__ALL__']
            if pair_status:
                pair_q = Q()
                has_pair_cond = False
                
                # 定义有效条件
                valid_sku = (~Q(local_sku__isnull=True) & ~Q(local_sku=""))
                valid_fnsku = (~Q(fnsku__isnull=True) & ~Q(fnsku=""))
                
                if 'paired' in pair_status:
                    # 必须都有值
                    pair_q |= (valid_sku & valid_fnsku)
                    has_pair_cond = True
                if 'unpaired' in pair_status:
                    # 任意一个无值
                    pair_q |= (~(valid_sku & valid_fnsku))
                    has_pair_cond = True
                
                if has_pair_cond:
                    queryset = queryset.filter(pair_q)

        # 5. Listing 状态筛选 (on, off, deleted)
        # status: 1=on, 0=off; is_delete: 1=deleted
        listing_status_filters = get_param_list('listingStatus')
        has_status_filter = False
        
        if listing_status_filters:
            listing_status_filters = [s for s in listing_status_filters if s != '__ALL__']
            if listing_status_filters:
                status_q = Q()
                
                if 'on' in listing_status_filters:
                    status_q |= Q(status=1, is_delete=0)
                    has_status_filter = True
                if 'off' in listing_status_filters:
                    status_q |= Q(status=0, is_delete=0)
                    has_status_filter = True
                if 'deleted' in listing_status_filters:
                    status_q |= Q(is_delete=1)
                    has_status_filter = True
                
                if has_status_filter:
                    queryset = queryset.filter(status_q)
        
        if not has_status_filter:
            # 默认不显示已删除
            queryset = queryset.filter(is_delete=0)

        # 6. 时间筛选: reportUpdatedAt -> open_date_display (新建时间)
        date_range = get_param_list('reportUpdatedAt')
        if date_range and len(date_range) >= 2:
            start_date = date_range[0]
            end_date = date_range[1]
            if start_date and end_date:
                # 兼容只传日期的情况，结束日期补充到当天最晚
                if len(end_date) == 10: 
                    end_date = end_date + " 23:59:59"
                queryset = queryset.filter(open_date_display__gte=start_date, open_date_display__lte=end_date)

        # 7. 负责人筛选 (owner) - 位于关键词搜索之前
        owners = get_param_list('owner')
        if owners:
            owners = [o for o in owners if o != '__ALL__']
            if owners:
                owner_q = Q()
                for owner_name in owners:
                    # principal_info 是 JSONField，结构如 [{"principal_name": "xxx", ...}]
                    # 使用 icontains 模糊匹配 JSON 字符串中的名称
                    owner_q |= Q(principal_info__icontains=owner_name)
                queryset = queryset.filter(owner_q)

        # 8. 关键词搜索
        if keyword:
            # 支持逗号分隔的多值搜索 (支持中英文逗号)
            keywords_list = [k.strip() for k in keyword.replace('，', ',').split(',') if k.strip()]
            
            if keywords_list:
                search_q = Q()
                if search_type == 'seller_sku':  # MSKU
                    for key in keywords_list:
                        search_q |= Q(seller_sku__icontains=key)
                    queryset = queryset.filter(search_q)
                elif search_type == 'asin':      # ASIN
                    for key in keywords_list:
                        search_q |= Q(asin__icontains=key)
                    queryset = queryset.filter(search_q)
                elif search_type == 'sku':       # 本地 SKU
                    for key in keywords_list:
                        search_q |= Q(local_sku__icontains=key)
                    queryset = queryset.filter(search_q)
                elif search_type == 'tag':       # 节气标签
                    # 先查出包含这些标签的 ASIN
                    tag_q = Q()
                    for key in keywords_list:
                        # JSONField 模糊搜索 (依赖数据库实现，SQLite/MySQL在特定版本支持)
                        # 这里假设 tags 存的是 ["tag1", "tag2"] 字符串列表
                        tag_q |= Q(tags__icontains=key)
                    
                    matched_asins = SolarTermTag.objects.filter(tag_q).values_list('asin', flat=True)
                    queryset = queryset.filter(asin__in=matched_asins)



        # 8. 排序逻辑
        sort_prop = params.get('sort')    # 前端字段名，如 salesToday
        sort_order = params.get('order')  # ascending / descending
        
        if sort_prop and sort_order:
            # 排序方向
            prefix = "" if sort_order == 'ascending' else "-"
            
            # 字段映射与预处理
            # 注意: 部分字段可能是字符串存数字，需 Cast
            if sort_prop == 'createTime':
                # 新建时间: 使用 open_date_display (新建时间)
                # 注意: 前端传 sort_order="ascending", prefix="" -> A-Z (升序，旧->新)
                #      前端传 sort_order="descending", prefix="-" -> Z-A (降序，新->旧)
                queryset = queryset.order_by(f"{prefix}open_date_display")
            elif sort_prop == 'msku':
                # MSKU 排序
                queryset = queryset.order_by(f"{prefix}seller_sku")

            elif sort_prop == 'skuName':
                # 品名/SKU 排序 (优先 Local SKU)
                # local_sku -> local_name
                queryset = queryset.order_by(f"{prefix}local_sku", f"{prefix}local_name")

            elif sort_prop == 'salesYesterday':
                # 昨日销量: yesterday_volume (String -> Int)
                queryset = queryset.annotate(
                    sorted_yesterday_vol=Cast('yesterday_volume', IntegerField())
                ).order_by(f"{prefix}sorted_yesterday_vol")
            
            elif sort_prop == 'rank':
                # 大类排名: seller_rank (Int)
                queryset = queryset.order_by(f"{prefix}seller_rank")

            elif sort_prop == 'openTime':
                # 开售时间: on_sale_time
                queryset = queryset.order_by(f"{prefix}on_sale_time")

            elif sort_prop == 'firstOrderTime':
                # 首单时间: first_order_time
                queryset = queryset.order_by(f"{prefix}first_order_time")
            
            # 以下字段暂无对应物理字段，或需关联查询，暂不支持服务器排序 (前端可点，但后端忽略或默认)
            # salesToday (今日销量) -> 暂无
            # profit (毛利润) -> 暂无
            # adCostYesterday (昨日广告费) -> 暂无
            # smallRank (小类排名) -> JSON, 暂不支持简单排序
            else:
                 pass # 保持默认排序

        total = queryset.count()
        
        # 分页
        start = (page_num - 1) * page_size
        end = start + page_size
        page_data = queryset[start:end]
        
        serializer = SalesProductListingSerializer(page_data, many=True)
        
        return Response({
            "code": 0,
            "message": "success",
            "error_details": [],
            "total": total,
            "data": serializer.data
        })

    @action(detail=False, methods=["post"], url_path="")
    def create(self, request):
        """
        创建 Listing
        唯一性校验: sid + seller_sku + fnsku + asin
        """
        data = request.data
        sid = data.get('sid')
        seller_sku = data.get('seller_sku')
        fnsku = data.get('fnsku')
        asin = data.get('asin')
        
        if not all([str(sid), seller_sku, fnsku, asin]):
             return drf_error("缺少关键字段: sid, seller_sku, fnsku, asin")

        # 检查重复 (仅检查未删除的)
        exists = SalesProductListing.objects.filter(
            sid=sid,
            seller_sku=seller_sku,
            fnsku=fnsku,
            asin=asin,
            is_delete=0
        ).exists()
        
        if exists:
            return drf_error("商品已存在")

        serializer = SalesProductListingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return drf_ok(serializer.data, msg="创建成功")
        else:
             return drf_error(f"校验失败: {serializer.errors}")

    @action(detail=False, methods=["put"], url_path=r"(?P<pk>[^/]+)")
    def update(self, request, pk=None):
        """
        更新 Listing (兼容创建：若 ID 不存在且提供关键字段，则新建)
        """
        obj = SalesProductListing.objects.filter(listing_id=pk, is_delete=0).first()
        if not obj and str(pk).isdigit():
             obj = SalesProductListing.objects.filter(id=pk, is_delete=0).first()
        
        data = request.data

        # 1. 存在则更新
        if obj:
            serializer = SalesProductListingSerializer(obj, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return drf_ok(serializer.data, msg="更新成功")
            else:
                return drf_error(f"校验失败: {serializer.errors}")

        # 2. 不存在则创建
        sid = data.get('sid')
        seller_sku = data.get('seller_sku')
        fnsku = data.get('fnsku')
        asin = data.get('asin')
        
        if not all([str(sid), seller_sku, fnsku, asin]):
             return drf_error("Listing 不存在，且缺少创建关键字段 (sid, seller_sku, fnsku, asin)", status=404)

        # 检查重复
        if SalesProductListing.objects.filter(
            sid=sid,
            seller_sku=seller_sku,
            fnsku=fnsku,
            asin=asin,
            is_delete=0
        ).exists():
             return drf_error("创建失败：商品已存在于其他记录")

        # 使用 pk 作为 listing_id (若非纯数字)
        create_data = data.copy()
        if pk and not str(pk).isdigit():
             create_data['listing_id'] = pk
        
        serializer = SalesProductListingSerializer(data=create_data)
        if serializer.is_valid():
            serializer.save()
            return drf_ok(serializer.data, msg="创建成功", status=201)
        else:
            return drf_error(f"创建校验失败: {serializer.errors}")

    @action(detail=False, methods=["delete"], url_path=r"(?P<pk>[^/]+)")
    def destroy(self, request, pk=None):
        """
        删除 Listing (软删除)
        """
        obj = SalesProductListing.objects.filter(listing_id=pk).first()
        if not obj and str(pk).isdigit():
             obj = SalesProductListing.objects.filter(id=pk).first()

        if not obj:
            return drf_error("Listing 不存在", status=404)
        
        obj.is_delete = 1
        obj.save()
        return drf_ok(msg="删除成功")

