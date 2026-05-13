/**
 * 数据采集卖家精灵账号 API（CrawlerSeller）。
 */
import request from "@/utils/request";

export interface CrawlerSellerVO {
  id?: string;
  username?: string;
  password?: string;
  status?: number;
  order_num?: number;
}

export interface CrawlerSellerForm {
  id?: string;
  username?: string;
  password?: string;
  status?: number;
  order_num?: number;
}

const CRAWLER_SELLER_BASE_URL = "/crawler/seller";

export const SellerAPI = {
  getList(params: any) {
    return request<any, CrawlerSellerVO[]>({
      url: `${CRAWLER_SELLER_BASE_URL}`,
      method: "get",
      params,
    });
  },
  getFormData(id: string) {
    return request<any, CrawlerSellerForm>({
      url: `${CRAWLER_SELLER_BASE_URL}/${id}/form`,
      method: "get",
    });
  },
  create(data: CrawlerSellerForm) {
    return request({ url: `${CRAWLER_SELLER_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: CrawlerSellerForm) {
    return request({ url: `${CRAWLER_SELLER_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${CRAWLER_SELLER_BASE_URL}/${ids}`, method: "delete" });
  },
};
