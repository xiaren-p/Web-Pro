/**
 * 数据采集卖家精灵账号 API（CrawlerSeller）。
 */
import request from "@/utils/request";

/** 卖家账号 VO。 */
export interface CrawlerSellerVO {
  id?: string;
  username?: string;
  password?: string;
  status?: number;
  order_num?: number;
}

/** 卖家账号表单。 */
export interface CrawlerSellerForm {
  id?: string;
  username?: string;
  password?: string;
  status?: number;
  order_num?: number;
}

const CRAWLER_SELLER_BASE_URL = "/crawler/seller";

export const SellerAPI = {
  /**
   * 获取卖家账号列表。
   *
   * @param params - 查询参数。
   * @returns 账号列表。
   */
  getList(params: Record<string, unknown>) {
    return request<any, CrawlerSellerVO[]>({ url: `${CRAWLER_SELLER_BASE_URL}`, method: "get", params });
  },
  /**
   * 获取账号编辑表单。
   *
   * @param id - 账号ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, CrawlerSellerForm>({ url: `${CRAWLER_SELLER_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 创建账号。
   *
   * @param data - 表单数据。
   */
  create(data: CrawlerSellerForm) {
    return request({ url: `${CRAWLER_SELLER_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新账号。
   *
   * @param id - 账号ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: CrawlerSellerForm) {
    return request({ url: `${CRAWLER_SELLER_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 批量删除账号。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${CRAWLER_SELLER_BASE_URL}/${ids}`, method: "delete" });
  },
};
