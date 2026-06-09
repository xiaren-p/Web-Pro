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
  effectiveStartDay: string;
  effectiveEnd: string;
  effectiveEndDay: string;
  categories: string[];
  unlimitedCategories: boolean;
  managers: (number | string)[];
  unlimitedManagers: boolean;
  tags: string[];
  unlimitedTags: boolean;
  comparisonTarget: string;
  comparisonMultiTargets: string[];
  conditionSets: RuleConditionSet[];
  linkedTimeRules: (number | string)[];
  linkedTimeRulesExclude: (number | string)[];
  bidAction: RuleAction;
  budgetAction: RuleAction;
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
  createdAt: string;
}
