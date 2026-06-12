"""SP 广告优化策略——执行编排服务（execution_service）。

按比对对象维度分派执行，支持全量执行和按维度单独调度。
"""
from __future__ import annotations

import logging
from typing import Any

from api_v2.services.ad_optimization.optimization_executor.executor_campaign import (
    execute_campaign_rules,
)
from api_v2.services.ad_optimization.optimization_executor.executor_keyword import (
    execute_keyword_rules,
)
from api_v2.services.ad_optimization.optimization_executor.executor_product_targeting import (
    execute_product_targeting_rules,
)
from api_v2.services.ad_optimization.optimization_executor.executor_targeting import (
    execute_targeting_rules,
)
from api_v2.services.ad_optimization.optimization_executor.placeholder_targets import (
    execute_ad_group_rules,
    execute_negative_targeting_rules,
    execute_search_terms_rules,
)

logger = logging.getLogger(__name__)

# 维度 → 执行函数映射
_DIMENSION_EXECUTORS: dict[str, Any] = {
    "campaign": execute_campaign_rules,
    "targeting": execute_targeting_rules,
    "keyword": execute_keyword_rules,
    "product_targeting": execute_product_targeting_rules,
    "ad_group": execute_ad_group_rules,
    "search_terms": execute_search_terms_rules,
    "negative_targeting": execute_negative_targeting_rules,
}


def execute_single_dimension(dimension: str) -> dict[str, Any]:
    """执行单个维度的优化策略规则。

    Args:
        dimension: 维度名称，必须是 _DIMENSION_EXECUTORS 中的键。

    Returns:
        该维度的执行结果字典。

    Raises:
        ValueError: 维度名称无效。
    """
    executor = _DIMENSION_EXECUTORS.get(dimension)
    if executor is None:
        raise ValueError(
            f"无效的维度名称: {dimension}，"
            f"可用值: {list(_DIMENSION_EXECUTORS.keys())}"
        )
    logger.info("[execution_service] 执行维度: %s", dimension)
    return executor()


def execute_all_dimensions() -> dict[str, Any]:
    """按维度依次执行全部优化策略规则。

    执行顺序：campaign → targeting → keyword → product_targeting
             → ad_group → search_terms → negative_targeting
    """
    results: dict[str, Any] = {}
    for dim in _DIMENSION_EXECUTORS:
        results[dim] = _DIMENSION_EXECUTORS[dim]()

    executed = sum(
        r.get("执行规则数", r.get("executed", 0))
        for r in results.values()
        if isinstance(r, dict)
    )
    logger.info("[execution_service] 全维度完成: total_executed=%d", executed)
    return results
