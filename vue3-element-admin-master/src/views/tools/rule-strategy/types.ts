/**
 * SP 广告规则策略类型定义。
 * 所属板块：tools / 广告规则策略。
 */

/** 单个指标条件（支持两段和范围模式） */
export interface ConditionWithRange {
  metric: string;
  operator: string;
  value: number;
  /** 是否为范围模式 (X > metric > Y) */
  isRange?: boolean;
  /** 范围模式下的第二个运算符 */
  operator2?: string;
  /** 范围模式下的第二个值 (下界) */
  value2?: number;
}

/** 一个条件组：时间范围 + N 个指标条件 */
export interface RuleConditionSet {
  days: number;
  conditions: ConditionWithRange[];
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
  /** 用户搜索词专属：添加关键词到手动广告 */
  addKeywordAction: string;
  addKeywordMatchType: string;
  addKeywordBidType: string;
  addKeywordMaxBid: number | null;
  addKeywordFixedBid: number | null;
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
