from rest_framework import viewsets
from django.db.models import Q
from api_v1.models import AdCampaign, AdMetricData
from api_v1.serializers import AdCampaignSerializer, AdMetricDataSerializer
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_ok

class AdCampaignViewSet(viewsets.ViewSet):
    """
    广告活动基础数据 (只提供查询)
    """
    
    def _serialize(self, obj):
        return AdCampaignSerializer(obj).data

    def list(self, request):
        qs = AdCampaign.objects.all().order_by("-id")
        
        keyword = request.query_params.get("keyword") or request.query_params.get("name")
        if isinstance(keyword, str) and keyword.strip():
            kw = keyword.strip()
            qs = qs.filter(
                Q(name__icontains=kw) |
                Q(store_name__icontains=kw) |
                Q(portfolio_name__icontains=kw) |
                Q(campaign_id__icontains=kw)
            )

        state = request.query_params.get('state')
        if state:
            qs = qs.filter(state__in=state.split(','))
            
        service_status = request.query_params.get('service_status')
        if service_status:
            qs = qs.filter(service_status__in=service_status.split(','))
            
        sponsored_type = request.query_params.get('sponsored_type')
        if sponsored_type:
            qs = qs.filter(sponsored_type__in=sponsored_type.split(','))
            
        targeting_type = request.query_params.get('targeting_type')
        if targeting_type:
            qs = qs.filter(targeting_type__in=targeting_type.split(','))
            
        bidding_type = request.query_params.get('bidding_type')
        if bidding_type:
            qs = qs.filter(bidding_type__in=bidding_type.split(','))
            
        portfolio_name = request.query_params.get('portfolio_name')
        if portfolio_name:
            qs = qs.filter(portfolio_name__in=portfolio_name.split(','))

        total, items, p_num, p_size = paginate_queryset(request, qs)
        
        # 指标表匹配 (名字不再使用 real-time)
        campaign_ids = [item.campaign_id for item in items if item.campaign_id]
        metric_qs = AdMetricData.objects.filter(campaign_id__in=campaign_ids)
        metric_map = {rt.campaign_id: AdMetricDataSerializer(rt).data for rt in metric_qs}
        
        res_list = []
        for item in items:
            base_dict = self._serialize(item)
            rt_dict = metric_map.get(item.campaign_id, {})
            base_dict.update(rt_dict)
            res_list.append(base_dict)

        data = {
            "total": total,
            "list": res_list,
            "pageNum": p_num,
            "pageSize": p_size
        }
        return drf_ok(data)




