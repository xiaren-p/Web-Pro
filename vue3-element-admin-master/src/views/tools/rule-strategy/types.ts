export interface ConditionWithRange {
  metric: string;
  operator: string;
  value: number;
  isRange?: boolean;
  operator2?: string;
  value2?: number;
}

export interface RuleConditionSet {
  /** 条件对象：仅投放/search_terms 时需要 */
  target: string;
  days: number;
  conditions: ConditionWithRange[];
}

/** 条件对象选项（仅投放/搜索词场景显示） */
export function getConditionTargetOptions(
  comparisonTarget: string
): { value: string; label: string; disabled?: boolean }[] {
  if (comparisonTarget === "search_terms") {
    return [
      { value: "campaign", label: "广告活动实体" },
      { value: "ad_group", label: "广告组实体", disabled: true },
      { value: "search_term", label: "搜索词实体" },
    ];
  }
  return [
    { value: "campaign", label: "广告活动实体" },
    { value: "ad_group", label: "广告组实体", disabled: true },
    { value: "targeting", label: "投放实体" },
  ];
}

export interface RuleAction {
  type: string;
  value: number;
  limit: number | null;
}

export interface OtherAction {
  type: string;
  notify: boolean;
}

/** 一条投放竞价操作项（Campaign AUTO/MANUAL 专属） */
export interface TargetingBidAction {
  targetingGroups: string[];
  unlimitedTargeting: boolean;
  conditionSets: RuleConditionSet[];
  bidAction: RuleAction;
}

export interface RuleFormData {
  id: string;
  name: string;
  shops: (number | string)[];
  status: "active" | "inactive";

  /** 广告类型：不限 | 手动 | 自动 */
  adType: "all" | "manual" | "auto";

  effectiveType: "date_range" | "within_days" | "beyond_days";
  effectiveDaysStart: number;
  effectiveDaysEnd: number;
  effectiveStart: string;
  effectiveStartDay: string;
  effectiveEnd: string;
  effectiveEndDay: string;

  /** 比对对象 */
  comparisonTarget: string;
  comparisonMultiTargets: string[];

  categories: string[];
  unlimitedCategories: boolean;
  managers: (number | string)[];
  unlimitedManagers: boolean;
  tags: string[];
  unlimitedTags: boolean;

  /** 自动定位组（仅 AUTO + 投放 + 定位组投放 时显示） */
  autoTargetingGroups: string[];
  unlimitedAutoTargeting: boolean;

  conditionSets: RuleConditionSet[];
  linkedTimeRules: (number | string)[];
  linkedTimeRulesExclude: (number | string)[];

  /** 投放竞价操作列表（Campaign AUTO/MANUAL 时使用） */
  targetingBidActions: TargetingBidAction[];

  bidAction: RuleAction;
  budgetAction: RuleAction;
  otherAction: OtherAction;
  negativeAction: string;
  addKeywordAction: string;
  addKeywordMatchType: string;
  addKeywordBidType: string;
  addKeywordMaxBid: number | null;
  addKeywordFixedBid: number | null;
}

export interface AdRule extends RuleFormData {
  createdAt: string;
  updatedAt: string;
}

export interface AdRuleGroup {
  id: string;
  name: string;
  rules: AdRule[];
  executionCycle: number;
  createdAt: string;
}
