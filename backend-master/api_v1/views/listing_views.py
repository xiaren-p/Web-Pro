from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from api_v1.utils.responses import drf_ok, drf_error
from api_v1.models import LxListingInfo, LxProductInfo, LxListingMetrics, LxSellers, LxListingRemark, CurrencyIcon
from django.db.models import Q, IntegerField, FloatField, Subquery, OuterRef
from django.db.models.functions import Cast, Coalesce
import uuid


class SalesProductListingViewSet(ViewSet):
    @action(detail=False, methods=["get"], url_path="page")
    def page(self, request):
        """获取 Listing 列表分页数据"""
        params = request.query_params
        page_num = int(params.get('pageNum', 1))
        page_size = int(params.get('pageSize', 50))
        
        keyword = params.get('keywords', '')
        search_type = params.get('searchType', '')

        def get_param_list(key):
            raw = params.getlist(key) or params.getlist(f"{key}[]")
            result = []
            for item in raw:
                if ',' in item:
                    result.extend([x.strip() for x in item.split(',') if x.strip()])
                else:
                    if item.strip():
                        result.append(item.strip())
            return result
        
        queryset = LxListingInfo.objects.select_related('product_link', 'shop_link', 'metrics', 'remark').all()

        countries = get_param_list('country')
        if countries:
            countries = [c for c in countries if c != '__ALL__']
            if countries:
                queryset = queryset.filter(shop_link__country__in=countries)

        shop_ids = get_param_list('shopId')
        if shop_ids:
            shop_ids = [s for s in shop_ids if s != '__ALL__']
            if shop_ids:
                queryset = queryset.filter(shop_link_id__in=shop_ids)

        cat_types = get_param_list('categoryType')
        if cat_types:
            cat_types = [c for c in cat_types if c != '__ALL__']
            if cat_types:
                cat_q = Q()
                for ct in cat_types:
                    if ct == '无':
                        cat_q |= Q(product_link__assort__isnull=True) | Q(product_link__assort='')
                    else:
                        cat_q |= Q(product_link__assort__icontains=ct)
                queryset = queryset.filter(cat_q)

        pair_status = get_param_list('pairStatus')
        if pair_status:
            pair_status = [p for p in pair_status if p != '__ALL__']
            if pair_status:
                valid_msku = (~Q(msku__isnull=True) & ~Q(msku=""))
                valid_fnsku = (~Q(fnsku__isnull=True) & ~Q(fnsku=""))
                if 'paired' in pair_status and 'unpaired' not in pair_status:
                    queryset = queryset.filter(valid_msku & valid_fnsku)
                elif 'unpaired' in pair_status and 'paired' not in pair_status:
                    queryset = queryset.filter(~(valid_msku & valid_fnsku))

        listing_status_filters = get_param_list('listingStatus')
        has_status_filter = False
        if listing_status_filters:
            listing_status_filters = [s for s in listing_status_filters if s != '__ALL__']
            if listing_status_filters:
                status_q = Q()
                for st in listing_status_filters:
                    if st == 'on': status_q |= Q(status=1)
                    if st == 'off': status_q |= Q(status=0)
                    if st == 'deleted': status_q |= Q(status=2)
                queryset = queryset.filter(status_q)
                has_status_filter = True
        
        if not has_status_filter:
            queryset = queryset.filter(status__in=[0, 1])

        date_range = get_param_list('reportUpdatedAt')
        if date_range and len(date_range) >= 2:
            start_date, end_date = date_range[0], date_range[1]
            if start_date and end_date:
                if len(end_date) == 10: end_date += " 23:59:59"
                queryset = queryset.filter(open_date_time__gte=start_date, open_date_time__lte=end_date)

        owners = get_param_list('owner')
        if owners:
            owners = [o for o in owners if o != '__ALL__']
            if owners:
                owner_q = Q()
                for owner_uid in owners:
                    owner_q |= Q(product_link__principal_list__icontains=owner_uid)
                queryset = queryset.filter(owner_q)

        if keyword:
            keywords_list = [k.strip() for k in keyword.replace('，', ',').split(',') if k.strip()]
            if keywords_list:
                search_q = Q()
                for key in keywords_list:
                    if search_type == 'seller_sku':
                        search_q |= Q(msku__icontains=key)
                    elif search_type == 'asin':
                        search_q |= Q(product_link_id__icontains=key)
                    elif search_type == 'sku':
                        search_q |= Q(product_link__local_sku__icontains=key)
                    elif search_type == 'tag':
                        search_q |= Q(product_link__label__icontains=key)
                queryset = queryset.filter(search_q)

        sort_prop = params.get('sort')
        sort_order = params.get('order')
        
        if sort_prop and sort_order:
            prefix = "" if sort_order == 'ascending' else "-"
            if sort_prop == 'createTime': queryset = queryset.order_by(f"{prefix}open_date_time", "-id")
            elif sort_prop == 'msku': queryset = queryset.order_by(f"{prefix}msku", "-id")
            elif sort_prop == 'skuName': queryset = queryset.order_by(f"{prefix}product_link__local_sku", f"{prefix}product_link__local_name", "-id")
            elif sort_prop == 'salesYesterday':
                queryset = queryset.annotate(sorted_yesterday_vol=Cast('metrics__yesterday_volume', IntegerField())).order_by(f"{prefix}sorted_yesterday_vol", "-id")
            elif sort_prop == 'rank': queryset = queryset.order_by(f"{prefix}seller_rank", "-id")
            elif sort_prop == 'openTime': queryset = queryset.order_by(f"{prefix}on_sale_time", "-id")
            elif sort_prop == 'firstOrderTime': queryset = queryset.order_by(f"{prefix}first_order_time", "-id")
            else: queryset = queryset.order_by("-updated_at", "-id")
        else:
            queryset = queryset.order_by("-updated_at", "-id")

        total = queryset.count()
        page_data = list(queryset[(page_num - 1) * page_size : page_num * page_size])

        listing_ids = [item.id for item in page_data]
        from api_v1.models import LxOrderProfit
        profits = LxOrderProfit.objects.filter(listing_id__in=listing_ids).order_by('-report_date')
        profit_map = {}
        for p in profits:
            if p.listing_id not in profit_map:
                profit_map[p.listing_id] = {
                    'gross_profit': float(p.gross_profit) if p.gross_profit else 0.0,
                    'gross_margin': float(p.gross_margin) if p.gross_margin else 0.0,
                }
        
        icon_objs = CurrencyIcon.objects.all()
        icon_map = {o.country: o.icon for o in icon_objs}

        data_list = []
        for item in page_data:
            m = getattr(item, 'metrics', None)
            p = getattr(item, 'product_link', None)
            s = getattr(item, 'shop_link', None)
            
            principal_info = p.principal_list if p and p.principal_list else []
            # Extract realname for frontend
            for p_info in principal_info:
                if isinstance(p_info, dict):
                    realname = p_info.get('realname') or p_info.get('principal_name') or p_info.get('uid')
                    p_info['realname'] = realname
                    p_info['principal_name'] = realname # backward compatibility
            
            data_list.append({
                "id": item.id,
                "listing_id": str(item.id),
                "sid": item.shop_link_id,
                "marketplace": s.country if s else "",
                "shop_name": s.name if s else "",
                "country_code": s.country_code if s else "",
                "currency_icon": icon_map.get(s.country_code, "") if s else "",
                "seller_sku": item.msku or "",
                "fnsku": item.fnsku or "",
                "asin": item.product_link_id or "",
                "parent_asin": item.parent_asin or "",
                "small_image_url": p.image if p else "",
                "status": 1 if item.status == 1 else 0,
                "is_delete": 1 if item.status == 2 else 0,
                "item_name": item.item_name or "",
                "local_sku": p.local_sku if p else "",
                "local_name": p.local_name if p else "",
                "price": float(m.price) if m and m.price else 0,
                "landed_price": float(m.landed_price) if m and m.landed_price else 0,
                "listing_price": float(m.listing_price) if m and m.listing_price else 0,
                "b2b_price": m.b2b_price if m and m.b2b_price else "",
                "fba_fee": float(m.fba_fee) if m and m.fba_fee else 0,
                "referral_fee": float(m.referral_fee) if m and m.referral_fee else 0,
                "yesterday_spend": float(m.yesterday_spend) if m and m.yesterday_spend else 0,
                "seven_spend": float(m.seven_spend) if m and m.seven_spend else 0,
                "fourteen_spend": float(m.fourteen_spend) if m and m.fourteen_spend else 0,
                "thirty_spend": float(m.thirty_spend) if m and m.thirty_spend else 0,
                "afn_fulfillable_quantity": int(m.afn_fulfillable_quantity) if m and m.afn_fulfillable_quantity else 0,
                "yesterday_volume": str(m.yesterday_volume) if m else "0",
                "total_volume": str(m.total_volume) if m else "0",
                "fourteen_volume": str(m.fourteen_volume) if m else "0",
                "thirty_volume": str(m.thirty_volume) if m else "0",
                "yesterday_amount": str(m.yesterday_amount) if m else "0.00",
                "seven_amount": str(m.seven_amount) if m else "0.00",
                "fourteen_amount": str(m.fourteen_amount) if m else "0.00",
                "thirty_amount": str(m.thirty_amount) if m else "0.00",
                "average_seven_volume": str(m.average_seven_volume) if m else "0.00",
                "average_fourteen_volume": str(m.average_fourteen_volume) if m else "0.00",
                "average_thirty_volume": str(m.average_thirty_volume) if m else "0.00",
                "seller_rank": int(item.seller_rank) if item.seller_rank else 0,
                "small_rank": int(item.small_rank) if item.small_rank else 0,
                "seller_category": item.seller_category or "",
                "small_category": item.small_category or "",
                "seller_brand": p.brand if p else "",
                "principal_info": p.principal_list if p and p.principal_list else [],
                "open_date_display": item.open_date_time or "",
                "on_sale_time": item.on_sale_time or "",
                "first_order_time": item.first_order_time or "",
                "assort": p.assort if p else "",
                "label": p.label if p else "",
                "pair_type": item.pair_type or "",
                "amz_product_id": item.amz_product_id or "",
                "amz_product_id_type": item.amz_product_id_type or "",
                "variant_text": item.variant_text if item.variant_text else "",
                "review_num": item.reviews_num or 0,
                "last_star": str(item.stars) if item.stars else "0",
                "fulfillment_channel_type": item.fulfillment_channel_type or "",
                "remarks": item.remark.remark_text if hasattr(item, 'remark') and item.remark and item.remark.remark_text else "--",
                "profit_metrics": profit_map.get(item.id, {"gross_profit": 0.0, "gross_margin": 0.0})
            })

        return Response({"code": 0, "message": "success", "error_details": [], "total": total, "data": data_list})

    @action(detail=False, methods=["post"], url_path="labels/upsert")
    def upsert_labels(self, request):
        data = request.data
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return drf_error(msg="参数格式错误")
            
        asins = [item.get('asin') for item in data if item.get('asin')]
        if not asins:
            return drf_ok(msg="未提供任何 ASIN")
            
        products = LxProductInfo.objects.filter(asin__in=asins)
        prod_map = {p.asin: p for p in products}
        
        updates = []
        creates = []
        for item in data:
            asin = item.get('asin')
            if not asin:
                continue
            tags = item.get('tags', [])
            try:
                import json
                label_opt = json.dumps(tags, ensure_ascii=False)
            except Exception:
                label_opt = "[]"
            
            if asin in prod_map:
                prod = prod_map[asin]
                prod.label = label_opt
                updates.append(prod)
            else:
                creates.append(LxProductInfo(asin=asin, label=label_opt))
                
        if updates:
            LxProductInfo.objects.bulk_update(updates, ['label', 'updated_at'])
        if creates:
            LxProductInfo.objects.bulk_create(creates)
            
        return drf_ok(msg="标签保存成功")

    @action(detail=False, methods=["post"], url_path="assort/upsert")
    def upsert_assort(self, request):
        data = request.data
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return drf_error(msg="参数格式错误")
            
        asins = [item.get('asin') for item in data if item.get('asin')]
        if not asins:
            return drf_ok(msg="未提供任何 ASIN")
            
        products = LxProductInfo.objects.filter(asin__in=asins)
        prod_map = {p.asin: p for p in products}
        
        updates = []
        creates = []
        for item in data:
            asin = item.get('asin')
            if not asin:
                continue
            assort = item.get('assort', '')
            
            if asin in prod_map:
                prod = prod_map[asin]
                prod.assort = assort
                updates.append(prod)
            else:
                creates.append(LxProductInfo(asin=asin, assort=assort))
                
        if updates:
            LxProductInfo.objects.bulk_update(updates, ['assort', 'updated_at'])
        if creates:
            LxProductInfo.objects.bulk_create(creates)
            
        return drf_ok(msg="分类保存成功")


    @action(detail=False, methods=["post"], url_path="remark/upsert")
    def upsert_remark(self, request):
        data = request.data
        listing_id = data.get('listing_id')
        remark_text = data.get('remark', '')
        
        if not listing_id:
            return drf_error(msg="未提供 listing_id")
            
        try:
            listing = LxListingInfo.objects.get(id=listing_id)
        except LxListingInfo.DoesNotExist:
            return drf_error(msg="Listing不存在")
            
        obj, created = LxListingRemark.objects.update_or_create(
            listing=listing,
            defaults={'remark_text': remark_text}
        )
        return drf_ok(msg="备注保存成功")
