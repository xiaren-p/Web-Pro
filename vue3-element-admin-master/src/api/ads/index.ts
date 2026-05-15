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
