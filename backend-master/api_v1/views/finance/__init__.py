"""统计 / 月度亏损订单相关 ViewSet 包。

按一类一文件铁律拆分自原 ``api_v1/views/statistics_views.py``：

- :class:`StatisticsViewSet` -> :mod:`api_v1.views.finance.statistics_view`
- :class:`MonthlyLossViewSet` -> :mod:`api_v1.views.finance.monthly_loss_view`
- :class:`MonthlyLossFirst20ViewSet` -> :mod:`api_v1.views.finance.monthly_loss_first20_view`

模块级辅助函数（金额/比例格式化、Excel 导出缓存等）统一放在
:mod:`api_v1.views.finance._helpers`，以避免在 3 个视图间重复定义。
"""
from api_v1.views.finance.monthly_loss_first20_view import MonthlyLossFirst20ViewSet
from api_v1.views.finance.monthly_loss_view import MonthlyLossViewSet
from api_v1.views.finance.statistics_view import StatisticsViewSet

__all__ = [
    "StatisticsViewSet",
    "MonthlyLossViewSet",
    "MonthlyLossFirst20ViewSet",
]
