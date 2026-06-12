"""SP 广告优化策略——执行服务（optimization_executor）。

对 SpAdOptimizationStrategy 中已命中的 auto_rules 按比对对象维度执行操作。

当前支持：
  - campaign：广告活动维度（完整实现）
  - targeting：定位组投放维度（完整实现）
  - keyword：关键词投放维度（完整实现）
  - product_targeting：商品投放维度（完整实现）
  - ad_group：广告组维度（占位，开发中）
  - search_terms：用户搜索词维度（占位，开发中）
  - negative_targeting：否定投放维度（占位，开发中）
"""
from __future__ import annotations

from .executor_campaign import execute_campaign_rules

__all__ = [
    "execute_campaign_rules",
]
