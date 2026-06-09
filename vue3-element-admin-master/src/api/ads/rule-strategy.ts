/**
 * SP 广告规则策略 API 模块。
 * 所属板块：ads / 规则策略。
 */
import request from "@/utils/request";
import type { AdRule, AdRuleGroup } from "@/views/tools/rule-strategy/types";

// ── 通用响应 ──
interface PaginatedResponse<T> {
  total: number;
  list: T[];
  pageNum: number;
  pageSize: number;
}

// ── 规则 CRUD ──

/** 获取规则分页列表 */
export function fetchRuleList(params?: Record<string, any>): Promise<PaginatedResponse<AdRule>> {
  return request.get("/ads/rule-strategy/rules", { params });
}

/** 获取单条规则 */
export function getRule(id: string | number): Promise<AdRule> {
  return request.get(`/ads/rule-strategy/rules/${id}`);
}

/** 创建规则 */
export function createRule(data: Record<string, any>): Promise<AdRule> {
  return request.post("/ads/rule-strategy/rules", data);
}

/** 更新规则 */
export function updateRule(id: string | number, data: Record<string, any>): Promise<AdRule> {
  return request.put(`/ads/rule-strategy/rules/${id}/update`, data);
}

/** 删除规则 */
export function deleteRule(id: string | number): Promise<void> {
  return request.delete(`/ads/rule-strategy/rules/${id}/delete`);
}

// ── 规则组 CRUD ──

/** 获取规则组分页列表（含展开的 rules） */
export function fetchGroupList(
  params?: Record<string, any>
): Promise<PaginatedResponse<AdRuleGroup>> {
  return request.get("/ads/rule-strategy/groups", { params });
}

/** 获取单个规则组 */
export function getGroup(id: string | number): Promise<AdRuleGroup> {
  return request.get(`/ads/rule-strategy/groups/${id}`);
}

/** 创建规则组 */
export function createGroup(data: Record<string, any>): Promise<AdRuleGroup> {
  return request.post("/ads/rule-strategy/groups", data);
}

/** 更新规则组 */
export function updateGroup(id: string | number, data: Record<string, any>): Promise<AdRuleGroup> {
  return request.put(`/ads/rule-strategy/groups/${id}/update`, data);
}

/** 删除规则组 */
export function deleteGroup(id: string | number): Promise<void> {
  return request.delete(`/ads/rule-strategy/groups/${id}/delete`);
}

/** 添加规则到规则组 */
export function addRulesToGroup(
  groupId: string | number,
  ruleIds: (string | number)[]
): Promise<AdRuleGroup> {
  return request.post(`/ads/rule-strategy/groups/${groupId}/add-rules`, { ruleIds });
}

/** 从规则组移除规则 */
export function removeRuleFromGroup(
  groupId: string | number,
  ruleId: string | number
): Promise<AdRuleGroup> {
  return request.post(`/ads/rule-strategy/groups/${groupId}/remove-rule`, { ruleId });
}
