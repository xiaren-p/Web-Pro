import request from "@/utils/request";

/** 广告活动列表分页响应结构 */
interface AdCampaignsResponse {
  list: any[];
  total: number;
  summary?: Record<string, unknown>;
}

export function getAdCampaigns(data: any): Promise<AdCampaignsResponse> {
  return request({
    url: "/ads/campaigns",
    method: "post",
    data,
  });
}

export function getAdOptions(): Promise<any> {
  return request({
    url: "/ads/options",
    method: "post",
  });
}

export function getAdPortfolioOptions(data?: any): Promise<any> {
  return request({
    url: "/ads/portfolios/options",
    method: "post",
    data,
  });
}

/** 广告活动详情基础信息响应结构 */
export interface AdCampaignDetailResponse {
  campaign_id: string;
  name: string;
  targeting_type: string;
  state: string;
  sponsored_type: string;
}

/**
 * 获取单条广告活动的基础信息（用于详情页面包屑与标题展示）。
 *
 * @param {string} campaignId - 广告活动 ID
 * @param {string} profileId - 店铺 Profile ID
 * @returns {Promise<AdCampaignDetailResponse>} 广告活动基础信息
 */
export function getAdCampaignDetail(
  campaignId: string,
  profileId: string
): Promise<AdCampaignDetailResponse> {
  return request({
    url: "/ads/campaigns/detail",
    method: "get",
    params: { campaign_id: campaignId, profile_id: profileId },
  });
}

/** 广告组列表请求参数 */
export interface AdGroupsParams {
  campaign_id: string;
  profile_id: string;
  date_start?: string;
  date_end?: string;
  state?: string;
  keyword?: string;
  pageNum?: number;
  pageSize?: number;
}

/** 广告组列表分页响应结构 */
export interface AdGroupsResponse {
  list: any[];
  total: number;
  summary?: Record<string, unknown>;
  currency_icon?: string;
  pageNum: number;
  pageSize: number;
}

/**
 * 获取广告组列表及聚合指标。
 *
 * @param {AdGroupsParams} data - 查询参数，campaign_id 和 profile_id 为必填
 * @returns {Promise<AdGroupsResponse>} 广告组分页列表
 */
export function getAdGroups(data: AdGroupsParams): Promise<AdGroupsResponse> {
  return request({
    url: "/ads/ad-groups",
    method: "post",
    data,
  });
}

/** 广告投放列表请求参数 */
export interface AdsParams {
  campaign_id: string;
  profile_id: string;
  ad_group_id?: string;
  date_start?: string;
  date_end?: string;
  state?: string;
  service_status?: string;
  keyword?: string;
  pageNum?: number;
  pageSize?: number;
}

/** 广告投放列表分页响应结构 */
export interface AdsResponse {
  list: any[];
  total: number;
  summary?: Record<string, unknown>;
  currency_icon?: string;
  pageNum: number;
  pageSize: number;
}

/**
 * 获取广告投放列表及聚合指标。
 *
 * @param {AdsParams} data - 查询参数，ad_group_id、campaign_id 和 profile_id 均为必填
 * @returns {Promise<AdsResponse>} 广告投放分页列表
 */
export function getAds(data: AdsParams): Promise<AdsResponse> {
  return request({
    url: "/ads/ads",
    method: "post",
    data,
  });
}

/** 自动投放条款列表请求参数 */
export interface AutoTargetingParams {
  campaign_id: string;
  profile_id: string;
  date_start?: string;
  date_end?: string;
  state?: string;
  pageNum?: number;
  pageSize?: number;
}

/** 自动投放条款列表分页响应结构 */
export interface AutoTargetingResponse {
  list: any[];
  total: number;
  summary?: Record<string, unknown>;
  currency_icon?: string;
  pageNum: number;
  pageSize: number;
}

/**
 * 获取自动投放定向条款列表及聚合指标。
 *
 * @param {AutoTargetingParams} data - 查询参数，campaign_id 和 profile_id 为必填
 * @returns {Promise<AutoTargetingResponse>} 自动投放分页列表
 */
export function getAutoTargeting(data: AutoTargetingParams): Promise<AutoTargetingResponse> {
  return request({
    url: "/ads/auto-targeting",
    method: "post",
    data,
  });
}

/** 自动广告否定定向（否定商品）列表请求参数 */
export interface AutoNegativeTargetingParams {
  campaign_id: string;
  profile_id: string;
  date_start?: string;
  date_end?: string;
  state?: string;
  exp_type?: string;
  keyword?: string;
  pageNum?: number;
  pageSize?: number;
}

/** 自动广告否定定向列表分页响应结构 */
export interface AutoNegativeTargetingResponse {
  list: any[];
  total: number;
  summary?: Record<string, unknown>;
  currency_icon?: string;
  pageNum: number;
  pageSize: number;
}

/**
 * 获取自动广告否定定向（否定商品）列表及聚合指标。
 *
 * @param {AutoNegativeTargetingParams} data - 查询参数，campaign_id 和 profile_id 为必填
 * @returns {Promise<AutoNegativeTargetingResponse>} 否定定向分页列表
 */
export function getAutoNegativeTargeting(
  data: AutoNegativeTargetingParams
): Promise<AutoNegativeTargetingResponse> {
  return request({
    url: "/ads/auto-negative-targeting",
    method: "post",
    data,
  });
}

/** 否定关键词列表请求参数 */
export interface NegativeKeywordParams {
  campaign_id: string;
  profile_id: string;
  date_start?: string;
  date_end?: string;
  state?: string;
  match_type?: string;
  keyword?: string;
  pageNum?: number;
  pageSize?: number;
}

/** 否定关键词列表分页响应结构 */
export interface NegativeKeywordResponse {
  list: any[];
  total: number;
  summary?: Record<string, unknown>;
  currency_icon?: string;
  pageNum: number;
  pageSize: number;
}

/**
 * 获取否定关键词列表及聚合指标。
 *
 * @param {NegativeKeywordParams} data - 查询参数，campaign_id 和 profile_id 为必填
 * @returns {Promise<NegativeKeywordResponse>} 否定关键词分页列表
 */
export function getNegativeKeywords(data: NegativeKeywordParams): Promise<NegativeKeywordResponse> {
  return request({
    url: "/ads/negative-keywords",
    method: "post",
    data,
  });
}

// ── 关键词投放（手动/自动通用）───────────────────────────────

/** 关键词列表请求参数 */
export interface KeywordParams {
  campaign_id: string;
  profile_id: string;
  date_start?: string;
  date_end?: string;
  state?: string;
  match_type?: string;
  keyword?: string;
  pageNum?: number;
  pageSize?: number;
}

/** 关键词列表分页响应结构 */
export interface KeywordResponse {
  list: any[];
  total: number;
  summary?: Record<string, unknown>;
  currency_icon?: string;
  pageNum: number;
  pageSize: number;
}

/**
 * 获取关键词投放列表及聚合指标。
 *
 * @param {KeywordParams} data - 查询参数，campaign_id 和 profile_id 为必填
 * @returns {Promise<KeywordResponse>} 关键词投放分页列表
 */
export function getKeywords(data: KeywordParams): Promise<KeywordResponse> {
  return request({
    url: "/ads/keywords",
    method: "post",
    data,
  });
}

// ── 广告上传队列 ─────────────────────────────────────────────────────────────

import { requestV2 } from "@/utils/request";

/** 关键词条目：文本 + 月搜索量 */
export interface AdKeyword {
  keyword: string;
  monthly_search_volume: number;
}

/** 广告参数（由 xlsx 解析时写入，提交后只读） */
export interface AdQueueParams {
  skus: string[];
  keywords: AdKeyword[];
  daily_budget: number;
  default_bid: number;
  close_match_bid: number;
  loose_match_bid: number;
  substitutes_bid: number;
  complements_bid: number;
}

/** 广告各步骤产出 ID（每步成功后逐步填入） */
export interface AdQueueStepIds {
  campaign_id: string;
  ad_group_id: string;
  product_ad_ids: string[];
  keyword_ids: string[];
}

/** 广告上传队列单条记录结构 */
export interface AdQueueItem {
  id: number;
  campaign_name: string;
  shop: string;
  country: string;
  ad_type: string;
  ad_type_label: string;
  params: AdQueueParams;
  step_ids: AdQueueStepIds;
  parse_status: number;
  parse_status_label: string;
  msg: string;
  created_by_username: string;
  /** 格式化后的创建时间（"2026-05-30 10:23"），由后端定型，前端直接展示 */
  created_at_display: string;
}

/** 广告队列列表查询参数 */
export interface AdQueueQuery {
  page?: number;
  page_size?: number;
  parse_status?: number;
  shop?: string;
  country?: string;
  /** 创建时间起始日期，格式 YYYY-MM-DD */
  date_start?: string;
  /** 创建时间截止日期，格式 YYYY-MM-DD */
  date_end?: string;
  /**
   * 按用户 ID 过滤（仅管理员可用）。
   * 不传时默认查看当前登录用户自己的队列。
   */
  user_id?: number;
}

/** 广告队列列表分页响应结构 */
export interface AdQueueListResponse {
  total: number;
  page: number;
  page_size: number;
  list: AdQueueItem[];
}

/** 广告文件上传解析结果响应结构 */
export interface AdUploadResponse {
  count: number;
  success_count: number;
  failed_count: number;
  skipped_warnings: string[];
  list: AdQueueItem[];
}

/** 上传请求参数：包含文件、广告类型筛选、国家筛选和竞价设置 */
export interface AdUploadParams {
  /** 用户选择的 .xlsx 文件对象 */
  file: File;
  /** 广告类型筛选：都创建 / 仅自动 / 仅手动 */
  adTypeFilter: "all" | "auto" | "manual";
  /** 手动指定的国家代码列表；空数组表示按表需求自动读取 */
  countryFilter: string[];
  /** 每日预算（美元） */
  dailyBudget: number;
  /** 按国家覆盖每日预算（示例：{ PL: 2, SE: 9 }） */
  dailyBudgetByCountry?: Record<string, number>;
  /** 广告组默认竞价 */
  defaultBid: number;
  /** 自动广告——紧密匹配竞价 */
  closeMatchBid: number;
  /** 自动广告——同类匹配竞价 */
  looseMatchBid: number;
  /** 自动广告——宽泛匹配竞价 */
  substitutesBid: number;
  /** 自动广告——关联匹配竞价 */
  complementsBid: number;
}

/**
 * 上传 xlsx 文件，解析并批量创建广告上传队列记录。
 *
 * @param {AdUploadParams} params - 上传参数（文件、广告类型筛选、国家筛选）
 * @returns {Promise<AdUploadResponse>} 解析结果（含成功/失败条目统计与列表）
 */
export function uploadAdXlsx(params: AdUploadParams): Promise<AdUploadResponse> {
  const formData = new FormData();
  formData.append("file", params.file);
  formData.append("ad_type_filter", params.adTypeFilter);
  if (params.countryFilter.length > 0) {
    formData.append("country_filter", params.countryFilter.join(","));
  }
  formData.append("daily_budget", String(params.dailyBudget));
  if (params.dailyBudgetByCountry && Object.keys(params.dailyBudgetByCountry).length > 0) {
    formData.append("daily_budget_by_country", JSON.stringify(params.dailyBudgetByCountry));
  }
  formData.append("default_bid", String(params.defaultBid));
  formData.append("close_match_bid", String(params.closeMatchBid));
  formData.append("loose_match_bid", String(params.looseMatchBid));
  formData.append("substitutes_bid", String(params.substitutesBid));
  formData.append("complements_bid", String(params.complementsBid));
  return requestV2({
    url: "/ads/upload/",
    method: "post",
    data: formData,
    headers: { "Content-Type": "multipart/form-data" },
  });
}

/**
 * 分页查询广告上传队列记录列表。
 *
 * @param {AdQueueQuery} params - 查询参数（页码、状态过滤等）
 * @returns {Promise<AdQueueListResponse>} 分页列表响应
 */
export function getAdQueue(params: AdQueueQuery): Promise<AdQueueListResponse> {
  return requestV2({
    url: "/ads/queue/",
    method: "get",
    params,
  });
}

/**
 * 批量删除广告上传队列记录。
 *
 * @param {number[]} ids - 要删除的记录 ID 列表
 * @returns {Promise<{ deleted_count: number }>} 实际删除数量
 */
export function bulkDeleteAdQueue(ids: number[]): Promise<{ deleted_count: number }> {
  return requestV2({
    url: "/ads/queue/bulk-delete/",
    method: "delete",
    data: { ids },
  });
}

/**
 * 将失败队列记录重置为待提交（队列中）状态。
 *
 * @param {number[]} ids - 要重试的记录 ID 列表
 * @returns {Promise<{ retried_count: number }>} 实际重置的条数
 */
export function retryAdQueue(ids: number[]): Promise<{ retried_count: number }> {
  return requestV2({
    url: "/ads/queue/retry/",
    method: "post",
    data: { ids },
  });
}

// ── 分时调价策略 ─────────────────────────────────────────────────────────────

/** 下拉选项结构 */
export interface TimePricingOption {
  value: number | string;
  label: string;
}

/** 分时调价策略表单数据 */
export interface TimePricingFormData {
  id?: number;
  name: string;
  type?: string;
  shops: (number | string)[];
  status: number;
  start_time: number;
  end_time: number;
  base_value_type: number;
  base_fixed_value?: number | null;
  field_settings: {
    categories: string[];
    managers: (number | string)[];
    tags: string[];
  };
  time_mode: string;
  time_settings: Record<string, unknown>;
  callback_settings: Record<string, unknown>;
  weight: number;
  execution_result: number;
  creator?: string;
  created_at?: string;
  updated_at?: string;
}

/** 策略列表查询参数 */
export interface TimePricingQuery {
  pageNum?: number;
  pageSize?: number;
  keyword?: string;
  status?: number | string;
  timeMode?: string;
}

/** 策略列表响应 */
export interface TimePricingListResponse {
  total: number;
  list: TimePricingFormData[];
  pageNum: number;
  pageSize: number;
}

/**
 * 获取策略列表（分页 + 筛选）。
 */
export function getTimePricingList(params: TimePricingQuery): Promise<TimePricingListResponse> {
  return request({
    url: "/ads/time-pricing-strategy",
    method: "get",
    params,
  });
}

/**
 * 新增策略。
 */
export function createTimePricing(data: TimePricingFormData): Promise<TimePricingFormData> {
  return request({
    url: "/ads/time-pricing-strategy",
    method: "post",
    data,
  });
}

/**
 * 获取单条策略详情。
 */
export function getTimePricingDetail(id: number): Promise<TimePricingFormData> {
  return request({
    url: `/ads/time-pricing-strategy/${id}/form`,
    method: "get",
  });
}

/**
 * 更新策略。
 */
export function updateTimePricing(
  id: number,
  data: Partial<TimePricingFormData>
): Promise<TimePricingFormData> {
  return request({
    url: `/ads/time-pricing-strategy/${id}`,
    method: "put",
    data,
  });
}

/**
 * 删除策略（支持批量）。
 */
export function deleteTimePricing(ids: number[]): Promise<void> {
  return request({
    url: `/ads/time-pricing-strategy/${ids.join(",")}`,
    method: "delete",
  });
}

/**
 * 获取店铺下拉选项（LxAdsProfile.name + profile_id）。
 */
export function getShopOptions(): Promise<TimePricingOption[]> {
  return request({
    url: "/ads/time-pricing-strategy/shops",
    method: "get",
  });
}

/**
 * 获取负责人下拉选项（LxUser.realname + uid）。
 */
export function getManagerOptions(): Promise<TimePricingOption[]> {
  return request({
    url: "/ads/time-pricing-strategy/managers",
    method: "get",
  });
}

/**
 * 获取归类下拉选项（LxProductInfo.assort 去重）。
 */
export function getAssortOptions(): Promise<TimePricingOption[]> {
  return request({
    url: "/ads/time-pricing-strategy/assorts",
    method: "get",
  });
}

/**
 * 获取标签下拉选项（LxProductInfo.label 去重）。
 */
export function getLabelOptions(): Promise<TimePricingOption[]> {
  return request({
    url: "/ads/time-pricing-strategy/labels",
    method: "get",
  });
}
