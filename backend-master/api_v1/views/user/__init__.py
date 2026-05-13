"""用户与个人资料相关 ViewSet 包。

按一类一文件铁律拆分自原 ``api_v1/views/user_views.py``：

- :class:`UserViewSet` -> :mod:`api_v1.views.user.user_view`
- :class:`ProfileViewSet` -> :mod:`api_v1.views.user.profile_view`
"""
from api_v1.views.user.profile_view import ProfileViewSet
from api_v1.views.user.user_view import UserViewSet

__all__ = ["UserViewSet", "ProfileViewSet"]
