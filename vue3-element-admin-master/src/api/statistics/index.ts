/**
 * 统计报表 API：亏损订单缓存同步与读取入口。
 *
 * @deprecated 后端统计模块（MonthlyLossOrder/statistics views）已于 2026-07 清理，
 *   对应后端路由 /statistics/lossmakingorders_sync 和 /statistics/lossmakingorders_data
 *   不再存在。此模块保留供历史参考，调用将返回 404。
 */
import request from "@/utils/request";

const STAT_BASE_URL = "/statistics";

export const StatisticsAPI = {
  /**
   * 触发/检查缓存同步，返回 cache key 与同步元信息。
   *
   * @param body - 同步请求体。
   * @returns 同步状态。
   * @deprecated 后端已移除。
   */
  lossmakingOrdersSync(body: Record<string, unknown>) {
    return request<any, {
      key: string;
      sync_time: string | null;
      needs_refresh: boolean;
      syncing: boolean;
    }>({ url: `${STAT_BASE_URL}/lossmakingorders_sync`, method: "post", data: body });
  },
  /**
   * 根据 cache key 读取已缓存的 pick_fields 数据（分页）。
   *
   * @param body - 查询请求体。
   * @returns 分页数据。
   * @deprecated 后端已移除。
   */
  lossmakingOrdersData(body: Record<string, unknown>) {
    return request<any, { list: Record<string, unknown>[]; total: number; sync_time: string | null }>({
      url: `${STAT_BASE_URL}/lossmakingorders_data`, method: "post", data: body,
    });
  },
};
