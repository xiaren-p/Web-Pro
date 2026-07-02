"""天气查询服务。

封装高德天气 API 调用逻辑，与 HTTP 层解耦。
"""

import logging
from typing import Optional

import requests

from apps.common.selectors.weather_selector import WeatherSelector

logger = logging.getLogger(__name__)


class WeatherService:
    """高德天气查询服务。"""

    @staticmethod
    def get_live_weather(city: Optional[str] = None) -> dict:
        """调用高德 API 获取指定城市的实时天气。

        Args:
            city: 城市 adcode，不传时使用系统配置的默认城市。

        Returns:
            高德 API 返回的 lives[0] 字典（天气信息）。

        Raises:
            RuntimeError: 密钥未配置或上游 API 返回异常。
        """
        key = WeatherSelector.get_amap_key()
        if not key:
            raise WeatherServiceError("AMAP_KEY 未配置", code="AMAP_KEY_NOT_CONFIGURED")

        city_code = city or WeatherSelector.get_amap_city()
        base = WeatherSelector.get_amap_base()

        url = f"{base}/v3/weather/weatherInfo"
        params = {
            "key": key,
            "city": city_code,
            "extensions": "base",
            "output": "json",
        }

        logger.info("[WeatherService] 请求高德天气 API city=%s", city_code)
        try:
            resp = requests.get(url, params=params, timeout=5)
        except requests.RequestException as e:
            logger.error("[WeatherService] 高德 API 请求失败: %s", e, exc_info=True)
            raise WeatherServiceError(f"天气服务不可用: {e}", code="UPSTREAM_ERROR") from e

        if resp.status_code != 200:
            logger.error("[WeatherService] 高德 API 返回 %d", resp.status_code)
            raise WeatherServiceError(f"上游返回异常: {resp.status_code}", code="UPSTREAM_ERROR")

        data = resp.json()
        if data.get("status") != "1":
            logger.error("[WeatherService] 高德 API 业务错误: %s", data.get("info"))
            raise WeatherServiceError(f"高德 API 错误: {data.get('info')}", code="AMAP_API_ERROR")

        lives = data.get("lives", [])
        if not lives:
            raise WeatherServiceError("无天气数据", code="NO_DATA")

        return lives[0]


class WeatherServiceError(RuntimeError):
    """天气服务异常。

    Attributes:
        code: 业务错误码，用于前端展示和监控分类。
    """

    def __init__(self, message: str, code: str = "WEATHER_ERROR"):
        """初始化实例。"""
        super().__init__(message)
        self.code = code
