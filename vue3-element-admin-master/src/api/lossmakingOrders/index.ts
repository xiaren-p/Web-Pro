/**
 * 亏损订单（Lossmaking Orders）API 模块：仅做请求封装与轻量 DTO 归一，不做任何业务计算。
 * 所属板块：statistics / lossmakingOrders。
 */
import { ShopsAPI } from "@/api/shops";
import { StatisticsAPI } from "@/api/statistics";

/** 店铺下拉项原始结构（来自 ShopsAPI.getOptions）。 */
export interface ShopOptionRaw {
  id: string;
  name: string;
  country?: string;
}

/** 负责人下拉项归一结构。 */
export interface ListingOwnerOptionRaw {
  id: string;
  name: string;
}

/** 同步接口请求体。 */
export interface LossOrderSyncBody {
  startDate: string;
  endDate: string;
  currencyCode?: string;
}

/** 数据接口请求体。 */
export interface LossOrderDataBody {
  key?: string;
  startDate: string;
  endDate: string;
  currencyCode?: string;
  page?: number;
  page_size?: number;
  owners?: string[];
  searchValue?: string[];
  rule?: string;
  sids?: string[];
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

/** 同步接口响应结构。 */
export interface LossOrderSyncResponse {
  key?: string;
  syncing?: boolean;
  sync_time?: string | null;
  warning?: string;
  error?: string;
  msg?: string;
}

/** 数据接口响应结构。 */
export interface LossOrderDataResponse {
  list?: any[];
  total?: number;
  sync_time?: string | null;
}

/** 拉取店铺下拉项。 */
export async function fetchShopOptions(): Promise<ShopOptionRaw[]> {
  try {
    const res = await ShopsAPI.getOptions();
    return (res || []).map((it: any) => ({
      id: it.id,
      name: it.name,
      country: it.country,
    }));
  } catch (e) {
    console.error("fetchShopOptions error", e);
    return [];
  }
}

/** 拉取 Listing 负责人下拉项。 */
export async function fetchListingOwnerOptions(): Promise<ListingOwnerOptionRaw[]> {
  try {
    const res = await ShopsAPI.getOwners();
    return (res || []).map((it: any) => ({
      id: it.id || it.value,
      name: it.label || it.name || it.realname,
    }));
  } catch (e) {
    console.error("fetchListingOwnerOptions error", e);
    return [];
  }
}

/** 同步接口：以日期 + 币种作为缓存 key，返回 syncing 状态与 sync_time。 */
export function fetchLossOrderSync(body: LossOrderSyncBody): Promise<LossOrderSyncResponse> {
  return StatisticsAPI.lossmakingOrdersSync(body);
}

/** 数据接口：通过 sync 返回的 key 拉取分页数据。 */
export function fetchLossOrderData(body: LossOrderDataBody): Promise<LossOrderDataResponse> {
  return StatisticsAPI.lossmakingOrdersData(body);
}
