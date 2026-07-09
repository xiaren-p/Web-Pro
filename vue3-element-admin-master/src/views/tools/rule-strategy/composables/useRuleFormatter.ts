import { ACTION_LABEL, NO_VALUE_ACTIONS, type AdRule } from "../types"

const METRIC_LABEL: Record<string, string> = {
  cost: "花费",
  sales: "广告销售额",
  same_sales: "直接销售额",
  orders: "广告订单",
  same_orders: "直接订单",
  units: "广告销量",
  clicks: "点击",
  impressions: "曝光量",
  ctr: "CTR",
  cpc: "CPC",
  cpa: "CPA",
  acos: "ACoS",
  roas: "ROAS",
  cvr: "CVR",
  spend_rate: "花费占比",
  sales_rate: "销售额占比",
  is_ratio: "IS",
}

const OP_LABEL: Record<string, string> = {
  ">": ">",
  "<": "<",
  ">=": "≥",
  "<=": "≤",
  "==": "=",
  "!=": "≠",
}

function formatSingleCondition(c: Record<string, any>): string {
  const m = METRIC_LABEL[c.metric] || c.metric || "?"
  if (c.isRange && c.operator2) {
    const o2 = OP_LABEL[c.operator2] || c.operator2
    const o = OP_LABEL[c.operator] || c.operator
    return `${c.value} ${o2} ${m} ${o} ${c.value2}`
  }
  return `${m} ${OP_LABEL[c.operator] || c.operator} ${c.value}`
}

function formatBidAction(ba: Record<string, any>, prefix: string = ""): string {
  if (!ba?.type || ba.type === "no_adjust") return ""
  const label = ACTION_LABEL[ba.type] || ba.type
  if (NO_VALUE_ACTIONS.has(ba.type)) return prefix ? `${prefix}: ${label}` : label
  const suffix = ba.type.includes("decrease") ? "↓" : "↑"
  const val = ba.type.includes("percent") ? `${ba.value}%` : `${ba.value}`
  const text = `${label} ${val} ${suffix}`
  return prefix ? `${prefix}: ${text}` : text
}

export function useRuleFormatter() {
  function getRuleSummary(rule: AdRule): string {
    if (!rule.conditionSets?.length) return "-"
    return rule.conditionSets
      .map((cs) => {
        const conds = (cs.conditions || []).map(formatSingleCondition).join(",\n")
        return conds ? `近${cs.days}天: ${conds}` : `近${cs.days}天: 无条件`
      })
      .join(" | ")
  }

  function formatActions(rule: AdRule): string {
    const parts: string[] = []

    // targeting_bid_actions（campaign 维度）
    for (const tba of rule.targetingBidActions || []) {
      if (!tba.bidAction?.type || tba.bidAction.type === "no_adjust") continue
      const groups = tba.unlimitedTargeting
        ? "全部定位组"
        : (tba.targetingGroups || []).join("、")
      const actionText = formatBidAction(tba.bidAction)
      if (actionText) parts.push(`${groups} ${actionText}`)
    }

    // bidAction（非 campaign 维度，或者 targetingBidActions 为空时的 fallback）
    if (!parts.length) {
      const baText = formatBidAction(rule.bidAction || {})
      if (baText) parts.push(baText)
    }

    // 预算操作
    const bg = rule.budgetAction
    if (bg?.type && bg.type !== "no_adjust") {
      const label = ACTION_LABEL[bg.type] || bg.type
      const suffix = bg.type.includes("increase") ? "↑" : "↓"
      parts.push(`${label} ${bg.value}/天 ${suffix}`)
    }

    // 搜索词操作
    if (rule.negativeAction) {
      parts.push(ACTION_LABEL[rule.negativeAction] || rule.negativeAction)
    }
    if (rule.addKeywordAction) {
      parts.push(ACTION_LABEL[rule.addKeywordAction] || rule.addKeywordAction)
    }

    return parts.length > 0 ? parts.join(" · ") : "-"
  }

  return { getRuleSummary, formatActions }
}
