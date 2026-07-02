"""天气配置查询。

从系统配置表（apps.system.models.Config）读取高德 API 相关参数，
读不到时返回预设的兜底默认值。
"""

from apps.system.models import Config

_AMAP_KEY = "AMAP_KEY"
_AMAP_CITY = "AMAP_CITY"
_AMAP_BASE = "AMAP_BASE"
_DEFAULT_CITY = "440605"
_DEFAULT_BASE = "https://restapi.amap.com"


class WeatherSelector:
    """天气相关配置查询。"""

    @staticmethod
    def get_amap_key() -> str:
        """从 Config 表读取高德 API 密钥。

        Returns:
            密钥字符串；未配置时返回空字符串。
        """
        return _config_val(_AMAP_KEY)

    @staticmethod
    def get_amap_city() -> str:
        """读取默认城市 adcode。

        Returns:
            adcode 字符串，默认 440605（佛山南海区）。
        """
        return _config_val(_AMAP_CITY, _DEFAULT_CITY)

    @staticmethod
    def get_amap_base() -> str:
        """读取高德 API 基础地址。

        Returns:
            URL 字符串，默认 https://restapi.amap.com。
        """
        return _config_val(_AMAP_BASE, _DEFAULT_BASE)


def _config_val(key: str, fallback: str = "") -> str:
    """从系统配置表读取参数值。

    Args:
        key: Config 表中的参数键。
        fallback: 参数未配置时的兜底默认值。

    Returns:
        参数值字符串。
    """
    try:
        conf = Config.objects.filter(key=key, status=True).first()
        if conf and conf.value.strip():
            return conf.value.strip()
    except Exception:
        pass
    return fallback
