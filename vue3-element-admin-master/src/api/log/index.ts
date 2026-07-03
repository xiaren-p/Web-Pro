/**
 * 操作日志与访问统计 API。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

/** 日志分页查询参数。 */
export interface LogPageQuery extends PageQuery {
  keywords?: string;
  createTime?: [string, string];
}

/** 日志分页列表项。 */
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

/** 访问统计 VO。 */
export interface VisitStatsVO {
  todayUvCount: number;
  totalUvCount: number;
  uvGrowthRate: number;
  todayPvCount: number;
  totalPvCount: number;
  pvGrowthRate: number;
}

/** 访问趋势 VO。 */
export interface VisitTrendVO {
  dates: string[];
  pvList: number[];
  uvList: number[];
  ipList: number[];
}

const LOG_BASE_URL = "/logs";

export const LogAPI = {
  /**
   * 分页查询操作日志。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getPage(params: LogPageQuery) {
    return request<any, PageResult<LogPageVO[]>>({
      url: `${LOG_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  /**
   * 获取访问趋势数据。
   *
   * @param params - 查询参数。
   * @returns 访问趋势。
   */
  getVisitTrend(params?: Record<string, unknown>) {
    return request<any, VisitTrendVO>({
      url: `${LOG_BASE_URL}/visit-trend`,
      method: "get",
      params,
    });
  },
  /**
   * 获取访问统计数据。
   *
   * @param params - 查询参数。
   * @returns 访问统计。
   */
  getVisitStats(params?: Record<string, unknown>) {
    return request<any, VisitStatsVO>({
      url: `${LOG_BASE_URL}/visit-stats`,
      method: "get",
      params,
    });
  },
};
