/**
 * 店铺资源 API：店铺与 Listing 负责人下拉选项。
 */
import request from "@/utils/request";

const SHOPS_BASE_URL = "/shops";

export const ShopsAPI = {
  getOptions() {
    return request<any, any[]>({ url: `${SHOPS_BASE_URL}/options`, method: "get" });
  },
  getOwners() {
    return request<any, any[]>({ url: `${SHOPS_BASE_URL}/owners`, method: "get" });
  },
};
