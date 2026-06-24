import request from "@/utils/request";

/** 广告活动目标状态：启用 / 暂停 */
export type CampaignState = "enabled" | "paused";

/** 手动调整预算请求参数 */
export interface AdjustBudgetParams {
  /** 广告活动 ID */
  campaign_id: string | number;
  /** 店铺 Profile ID */
  profile_id: string | number;
  /** 调整后预算（必须 > 0） */
  budget_after: number;
}

/** 手动调整预算响应数据 */
export interface AdjustBudgetResponse {
  campaign_id: number;
  profile_id: number;
  /** 调整前预算（可能为 null） */
  budget_before: number | null;
  /** 调整后预算 */
  budget_after: number;
}

/** 手动调整状态请求参数 */
export interface AdjustStateParams {
  /** 广告活动 ID */
  campaign_id: string | number;
  /** 店铺 Profile ID */
  profile_id: string | number;
  /** 目标状态：启用 / 暂停 */
  state: CampaignState;
}

/** 手动调整状态响应数据 */
export interface AdjustStateResponse {
  campaign_id: number;
  profile_id: number;
  state: CampaignState;
}

/**
 * 手动调整广告活动预算：写 SpCampaignAdjustment 记录 + 更新 LxSpCampaign.daily_budget。
 *
 * 仅写入调整记录表与本地实体表，不触发亚马逊推送；实际推送由专门的触发处
 * 调用 api_v2 的 ads/campaign-adjustment/run/ 接口完成。
 *
 * @param {AdjustBudgetParams} data - 调整参数（campaign_id / profile_id / budget_after）
 * @returns {Promise<AdjustBudgetResponse>} 调整结果（含调整前后预算）
 * @throws {Error} 参数错误或广告活动不存在时抛出
 */
export function createManualBudgetAdjustment(
  data: AdjustBudgetParams
): Promise<AdjustBudgetResponse> {
  return request({
    url: "/ads/campaigns/adjust-budget",
    method: "post",
    data,
  });
}

/** 批量调整广告活动状态请求参数 */
export interface BatchAdjustCampaignStateParams {
  /** 广告活动列表，每项含 campaign_id + profile_id + state */
  items: Array<{
    campaign_id: string | number;
    profile_id: string | number;
    state: CampaignState;
  }>;
}

/** 批量调整广告活动预算请求参数 */
export interface BatchAdjustCampaignBudgetParams {
  /** 广告活动列表，每项含 campaign_id + profile_id + budget_after */
  items: Array<{
    campaign_id: string | number;
    profile_id: string | number;
    budget_after: number;
  }>;
}

/** 批量操作响应 */
export interface BatchAdjustCampaignResponse {
  success_count: number;
  failed_count: number;
  errors?: Array<{ campaign_id: string | number; message: string }>;
}

/**
 * 手动调整广告活动状态：写 SpCampaignAdjustment 记录 + 更新 LxSpCampaign.state。
 *
 * state=enabled 写 CAMPAIGN_ENABLE 类型，state=paused 写 CAMPAIGN_PAUSE 类型（复用）。
 * 仅写入调整记录表与本地实体表，不触发亚马逊推送；实际推送由专门的触发处
 * 调用 api_v2 的 ads/campaign-adjustment/run/ 接口完成。
 *
 * @param {AdjustStateParams} data - 调整参数（campaign_id / profile_id / state）
 * @returns {Promise<AdjustStateResponse>} 调整结果（含目标状态）
 * @throws {Error} 参数错误或广告活动不存在时抛出
 */
export function createCampaignStateAdjustment(
  data: AdjustStateParams
): Promise<AdjustStateResponse> {
  return request({
    url: "/ads/campaigns/adjust-state",
    method: "post",
    data,
  });
}

/**
 * 批量调整广告活动状态：为每个选中的广告活动写 SpCampaignAdjustment 记录 + 更新 LxSpCampaign.state。
 *
 * @param {BatchAdjustCampaignStateParams} data - 批量调整参数
 * @returns {Promise<BatchAdjustCampaignResponse>} 批量操作结果
 */
export function batchAdjustCampaignState(
  data: BatchAdjustCampaignStateParams
): Promise<BatchAdjustCampaignResponse> {
  return request({
    url: "/ads/campaigns/batch-adjust-state",
    method: "post",
    data,
  });
}

/**
 * 批量调整广告活动预算：为每个选中的广告活动写 SpCampaignAdjustment 记录 + 更新 LxSpCampaign.daily_budget。
 *
 * @param {BatchAdjustCampaignBudgetParams} data - 批量调整参数
 * @returns {Promise<BatchAdjustCampaignResponse>} 批量操作结果
 */
export function batchAdjustCampaignBudget(
  data: BatchAdjustCampaignBudgetParams
): Promise<BatchAdjustCampaignResponse> {
  return request({
    url: "/ads/campaigns/batch-adjust-budget",
    method: "post",
    data,
  });
}
