"""
广告服务状态（service_status）统一映射工具。

所有广告相关模型（广告活动、广告组、广告等）的 service_status
原始英文枚举值在此集中注册，包含：
- 中文展示文字（label）
- 前端徽标样式类型（type：success / warning / danger / default）

依据：查询 lx_campaign_info 与 lx_ad_group_info 表中实际出现的全量枚举值。
若未来数据中出现新枚举值，只需在此处追加，无需修改任何视图层代码。
"""

# ── 中文标签映射（原始枚举值 → 中文展示文字）────────────────────────────────
_LABEL_MAP: dict[str, str] = {
    # ── 广告活动层（lx_campaign_info） ──
    "CAMPAIGN_STATUS_ENABLED":      "投放中",
    "CAMPAIGN_PAUSED":              "广告活动已暂停",
    "CAMPAIGN_ARCHIVED":            "广告活动已归档",
    "CAMPAIGN_OUT_OF_BUDGET":       "超预算",
    "CAMPAIGN_INCOMPLETE":          "不完整",
    "ADVERTISER_PAYMENT_FAILURE":   "广告账号付款失败",
    "LANDING_PAGE_NOT_AVAILABLE":   "着陆页失效",
    "OTHER":                        "未知",

    # ── 广告组层（lx_ad_group_info） ──
    "AD_GROUP_STATUS_ENABLED":      "投放中",
    "AD_GROUP_PAUSED":              "广告组已暂停",
    "AD_GROUP_STATUS_PAUSED":       "已暂停",
    "AD_GROUP_ARCHIVED":            "已归档",

    # ── 通用（广告活动与广告组均可出现） ──
    "PORTFOLIO_OUT_OF_BUDGET":      "超预算",
}

# ── 前端徽标类型映射（原始枚举值 → CSS 类后缀：success / warning / danger / default）────
_TYPE_MAP: dict[str, str] = {
    # 绿色：正常投放中
    "CAMPAIGN_STATUS_ENABLED":      "success",
    "AD_GROUP_STATUS_ENABLED":      "success",

    # 橙色：人工/系统暂停（可恢复）
    "CAMPAIGN_PAUSED":              "warning",
    "AD_GROUP_PAUSED":              "warning",
    "AD_GROUP_STATUS_PAUSED":       "warning",

    # 红色：异常/超预算/归档/不可用
    "CAMPAIGN_ARCHIVED":            "danger",
    "CAMPAIGN_OUT_OF_BUDGET":       "danger",
    "CAMPAIGN_INCOMPLETE":          "danger",
    "ADVERTISER_PAYMENT_FAILURE":   "danger",
    "LANDING_PAGE_NOT_AVAILABLE":   "danger",
    "AD_GROUP_ARCHIVED":            "danger",
    "PORTFOLIO_OUT_OF_BUDGET":      "danger",
    "OTHER":                        "danger",
}


def resolve_service_status(status: str | None) -> dict[str, str]:
    """
    根据 service_status 原始值解析出展示所需的中文标签与前端徽标类型。

    统一出口函数：视图层调用此函数，避免在多处 switch/映射字典中重复定义。

    Args:
        status (str | None): 广告服务状态原始英文枚举值。

    Returns:
        dict[str, str]: 包含以下两个字段：
            - label (str): 中文显示文字，未知值原样返回，空值返回 "-"。
            - type  (str): 前端徽标样式类型（success / warning / danger / default）。

    Examples:
        >>> resolve_service_status("CAMPAIGN_STATUS_ENABLED")
        {'label': '投放中', 'type': 'success'}
        >>> resolve_service_status("UNKNOWN_VALUE")
        {'label': 'UNKNOWN_VALUE', 'type': 'default'}
        >>> resolve_service_status(None)
        {'label': '-', 'type': 'default'}
    """
    raw = (status or "").strip()
    return {
        "label": _LABEL_MAP.get(raw, raw) if raw else "-",
        "type":  _TYPE_MAP.get(raw, "default"),
    }
