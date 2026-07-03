/**
 * 店铺资源 API：店铺与 Listing 负责人下拉选项。
 */
import request from "@/utils/request";

/** 下拉选项。 */
interface OptionItem {
  value: string;
  label: string;
}

const SHOPS_BASE_URL = "/shops";

export const ShopsAPI = {
  /**
   * 获取店铺下拉选项。
   *
   * @returns 选项列表。
   */
  getOptions() {
    return request<any, OptionItem[]>({ url: `${SHOPS_BASE_URL}/options`, method: "get" });
  },
  /**
   * 获取 Listing 负责人下拉选项。
   *
   * @returns 选项列表。
   */
  getOwners() {
    return request<any, OptionItem[]>({ url: `${SHOPS_BASE_URL}/owners`, method: "get" });
  },
};
