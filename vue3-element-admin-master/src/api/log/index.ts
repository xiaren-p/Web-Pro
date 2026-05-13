/**
 * 操作日志与访问统计 API。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface LogPageQuery extends PageQuery {
  keywords?: string;
  createTime?: [string, string];
}

export interface LogPageVO {
  id: string;
  createTime?: string;
  operator?: string;
  module?: string;
  content?: string;
  ip?: string;
  region?: string;
  browser?: string;
  os?: string;
  executionTime?: number;
}

export interface VisitStatsVO {
  todayUvCount: number;
  totalUvCount: number;
  uvGrowthRate: number;
  todayPvCount: number;
  totalPvCount: number;
  pvGrowthRate: number;
}

export interface VisitTrendVO {
  dates: string[];
  pvList: number[];
  uvList: number[];
  ipList: number[];
}

const LOG_BASE_URL = "/logs";

export const LogAPI = {
  getPage(params: LogPageQuery) {
    return request<any, PageResult<LogPageVO[]>>({
      url: `${LOG_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  getVisitTrend(params?: any) {
    return request<any, VisitTrendVO>({
      url: `${LOG_BASE_URL}/visit-trend`,
      method: "get",
      params,
    });
  },
  getVisitStats(params?: any) {
    return request<any, VisitStatsVO>({
      url: `${LOG_BASE_URL}/visit-stats`,
      method: "get",
      params,
    });
  },
};
