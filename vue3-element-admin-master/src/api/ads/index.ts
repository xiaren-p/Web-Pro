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

// ── 广告上传队列 ─────────────────────────────────────────────────────────────

import { requestV2 } from "@/utils/request";

/** 广告上传队列单条记录结构 */
export interface AdQueueItem {
  id: number;
  campaign_name: string;
  shop: string;
  country: string;
  ad_type: string;
  ad_type_label: string;
  skus: string[];
  keywords: string[];
  parse_status: number;
  parse_status_label: string;
  msg: string;
  created_at: string;
}

/** 广告队列列表查询参数 */
export interface AdQueueQuery {
  page?: number;
  page_size?: number;
  parse_status?: number;
  shop?: string;
  country?: string;
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

/** 上传请求参数：包含文件、广告类型筛选和国家筛选 */
export interface AdUploadParams {
  /** 用户选择的 .xlsx 文件对象 */
  file: File;
  /** 广告类型筛选：都创建 / 仅自动 / 仅手动 */
  adTypeFilter: "all" | "auto" | "manual";
  /** 手动指定的国家代码列表；空数组表示按表需求自动读取 */
  countryFilter: string[];
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
