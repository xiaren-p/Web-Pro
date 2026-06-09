/**
 * SP 广告规则策略类型定义。
 * 所属板块：tools / 广告规则策略。
 */

/** 单个指标条件 */
export interface MetricCondition {
  metric: string;
  operator: string;
  value: number;
}

/** 一个条件组：时间范围 + N 个指标条件 */
export interface RuleConditionSet {
  days: number;
  conditions: MetricCondition[];
}

/** 规则表单数据（前端表单结构，也是提交给后端的格式） */
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
  conditionSets: RuleConditionSet[];
  linkedTimeRules: (number | string)[];
  linkedTimeRulesExclude: (number | string)[];
  actionType: string;
  actionValue: number;
  actionLimit: number | null;
}

/** 规则列表展示结构 */
export interface AdRule extends RuleFormData {
  createdAt: string;
  updatedAt: string;
}

/** 规则组 */
export interface AdRuleGroup {
  id: string;
  name: string;
  rules: AdRule[];
  createdAt: string;
}
