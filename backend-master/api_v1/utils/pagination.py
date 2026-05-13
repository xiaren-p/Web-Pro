"""统一分页工具

提供 paginate_queryset(request, queryset, default_page_size=10)
返回 (total, items, page_num, page_size)

读取参数：pageNum / pageSize
容错：非法数字回退默认

后续可扩展：动态最大 pageSize、排序字段统一处理、过滤器抽象。
"""
from typing import Tuple, Any
from django.db.models import QuerySet


def paginate_queryset(request, queryset: QuerySet, default_page_size: int = 10) -> Tuple[int, Any, int, int]:
    """分页工具：兼容 Django QuerySet 与 Python 序列（list/tuple）。

    - 如果传入为 None，返回 (0, [], 1, page_size)
    - 如果对象有 .count() 方法（通常为 QuerySet），使用它获取总数；否则尝试 len()
    """
    data = request.data if request.method == "POST" else request.query_params
    
    try:
        page_num = int(data.get('pageNum', 1))
    except Exception:
        page_num = 1
    try:
        page_size = int(data.get('pageSize', default_page_size))
    except Exception:
        page_size = default_page_size
    if page_num < 1:
        page_num = 1
    if page_size < 1:
        page_size = default_page_size

    if queryset is None:
        return 0, [], page_num, page_size

    # 兼容 QuerySet 或普通序列
    try:
        total = queryset.count() if hasattr(queryset, 'count') and callable(getattr(queryset, 'count')) else len(queryset)
    except Exception:
        # 最后兜底：尝试转换为 list
        try:
            seq = list(queryset)
            total = len(seq)
            queryset = seq
        except Exception:
            # 若仍失败，返回空结果集
            return 0, [], page_num, page_size

    start = (page_num - 1) * page_size
    end = start + page_size
    try:
        items = queryset[start:end]
    except Exception:
        # 若切片失败（例如 queryset 类型不支持切片），尝试转换为 list 后切片
        try:
            seq = list(queryset)
            items = seq[start:end]
        except Exception:
            items = []
    return total, items, page_num, page_size


from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    """
    DRF Standard pagination class.
    Accepts 'pageNum' (default 'page') and 'pageSize' (default 'page_size') query parameters.
    Default page size is 15.
    """
    page_query_param = 'pageNum'
    page_size_query_param = 'pageSize'
    page_size = 15
    max_page_size = 1000

