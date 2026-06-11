"""SP 广告优化策略——执行编排服务（execution_service）。

按比对对象维度分派执行：
  - campaign：广告活动维度（完整实现）
  - targeting：定位组维度（完整实现，LxSpTarget expression_type=auto）
  - keyword：关键词维度（完整实现，LxSpKeyword）
  - product_targeting：商品投放维度（完整实现，LxSpTarget expression_type=manual）
  - ad_group / search_terms / negative_targeting：占位
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


def execute_all_dimensions() -> dict[str, Any]:
    """按维度依次执行优化策略规则。

    执行顺序：
      campaign → targeting → keyword → product_targeting
      → ad_group（占位）→ search_terms（占位）→ negative_targeting（占位）
    """
    results: dict[str, Any] = {}

    # 完整实现
    results["campaign"] = execute_campaign_rules()
    results["定位组"] = execute_targeting_rules()
    results["关键词"] = execute_keyword_rules()
    results["商品投放"] = execute_product_targeting_rules()

    # 占位
    results["广告组"] = execute_ad_group_rules()
    results["用户搜索词"] = execute_search_terms_rules()
    results["否定投放"] = execute_negative_targeting_rules()

    executed = sum(
        r.get("执行规则数", r.get("executed", 0))
        for k, r in results.items()
        if isinstance(r, dict)
    )
    logger.info("[execution_service] 多维度完成: total_executed=%d", executed)

    return results
