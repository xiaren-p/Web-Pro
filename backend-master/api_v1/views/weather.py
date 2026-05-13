"""天气查询视图。

高德 API 配置优先从系统参数配置表（Config）中读取，读不到再降级到 settings.py。
可在前端"系统管理 → 参数配置"页面维护以下三个参数键：
  - AMAP_KEY   高德 Web API 密钥
  - AMAP_CITY  城市 adcode（默认 440605 佛山南海区）
  - AMAP_BASE  API 基础地址（默认 https://restapi.amap.com）
"""
import requests
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from api_v1.models import Config
from api_v1.utils.responses import drf_ok, drf_error


def _config_val(key: str, fallback: str = '') -> str:
    """
    从系统参数配置表读取参数值，读不到或值为空则返回 fallback 兜底默认值。

    Args:
        key (str): Config 表中的参数键。
        fallback (str): 参数未配置时的兜底默认值。

    Returns:
        str: 参数值字符串。
    """
    try:
        conf = Config.objects.filter(key=key, status=True).first()
        if conf and conf.value.strip():
            return conf.value.strip()
    except Exception:
        pass
    return fallback


class WeatherViewSet(viewsets.ViewSet):
    """天气查询接口。"""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def live(self, request):
        """获取实时天气（高德 API）。"""
        key = _config_val('AMAP_KEY')
        city = _config_val('AMAP_CITY', '440605')
        base = _config_val('AMAP_BASE', 'https://restapi.amap.com')

        if not key:
            return drf_error('AMAP_KEY not configured', status=503)

        url = f'{base}/v3/weather/weatherInfo'
        params = {
            'key': key,
            'city': city,
            'extensions': 'base',
            'output': 'json',
        }

        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1':
                    lives = data.get('lives', [])
                    if lives:
                        return drf_ok(lives[0])
                    return drf_error('No weather data found')
                return drf_error(f"Amap API Error: {data.get('info')}")
            return drf_error(f"Upstream Error: {resp.status_code}")
        except Exception as e:
            return drf_error(f"Fetch weather failed: {str(e)}")
