"""天气查询视图。

封装高德实时天气 API，委托给 WeatherService 处理所有业务逻辑。
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from api_v1.utils.responses import drf_ok, drf_error
from apps.common.services.weather_service import WeatherService, WeatherServiceError


class WeatherViewSet(viewsets.ViewSet):
    """天气查询接口。

    用于系统仪表盘天气展示，查询参数通过 Query String 传入。
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def live(self, request):
        """获取指定城市的实时天气。

        Query Params:
            city: 城市 adcode，不传时使用系统配置的默认城市（佛山南海区）。
        """
        city = request.query_params.get("city")
        try:
            data = WeatherService.get_live_weather(city)
            return drf_ok(data)
        except WeatherServiceError as e:
            return drf_error(str(e), code=e.code, status=503)
