/**
 * SP 广告规则策略类型定义。
 * 所属板块：tools / 广告规则策略。
 */

export interface ConditionWithRange {
  metric: string;
  operator: string;
  value: number;
  isRange?: boolean;
  operator2?: string;
  value2?: number;
}

export interface RuleConditionSet {
  days: number;
  conditions: ConditionWithRange[];
}

/** 单个竞价/预算操作 */
export interface RuleAction {
  type: string;
  value: number;
  limit: number | null;
}

export interface RuleFormData {
  id: string;
  name: string;
  shops: (number | string)[];
  status: "active" | "inactive";
  effectiveType: "date_range" | "within_days" | "beyond_days";
  effectiveDays: number;
  effectiveStart: string;
  effectiveEnd: string;
  categories: string[];
  unlimitedCategories: boolean;
  managers: (number | string)[];
  unlimitedManagers: boolean;
  tags: string[];
  unlimitedTags: boolean;
  comparisonTarget: string;
  /** 多选比对对象 (定位组投放/关键词投放/商品投放) */
  comparisonMultiTargets: string[];
  conditionSets: RuleConditionSet[];
  linkedTimeRules: (number | string)[];
  linkedTimeRulesExclude: (number | string)[];
  /** 通用竞价操作列表（可多条） */
  bidActions: RuleAction[];
  /** 通用预算操作列表（可多条） */
  budgetActions: RuleAction[];
  /** 搜索词专属：否定操作 */
  negativeAction: string;
  /** 搜索词专属：关键词投放 */
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
  createdAt: string;
}
