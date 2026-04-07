import requests
from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from api_v1.utils.responses import drf_ok, drf_error

class WeatherViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def live(self, request):
        key = getattr(settings, 'AMAP_KEY', '')
        city = getattr(settings, 'AMAP_CITY', '440605')
        base = getattr(settings, 'AMAP_BASE')
        
        if not key:
            return drf_error('AMAP_KEY not configured', status=503)

        url =  f'{base}/v3/weather/weatherInfo'
        params = {
            'key': key,
            'city': city,
            'extensions': 'base',
            'output': 'json'
        }

        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1':
                    lives = data.get('lives', [])
                    if lives:
                        return drf_ok(lives[0])
                    else:
                        return drf_error('No weather data found')
                else:
                    return drf_error(f"Amap API Error: {data.get('info')}")
            else:
                return drf_error(f"Upstream Error: {resp.status_code}")
        except Exception as e:
            return drf_error(f"Fetch weather failed: {str(e)}")
