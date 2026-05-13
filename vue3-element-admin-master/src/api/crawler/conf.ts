/**
 * 数据采集服务节点 API（CrawlerConf）。
 */
import request from "@/utils/request";

export interface CrawlerConfVO {
  id?: string;
  server_name?: string;
  node?: string;
  ip?: string;
  status?: number;
  order_num?: number;
}

export interface CrawlerConfForm {
  id?: string;
  server_name?: string;
  node?: string;
  ip?: string;
  status?: number;
  order_num?: number;
}

const CRAWLER_BASE_URL = "/crawler/conf";

export const CrawlerAPI = {
  getList(params: any) {
    return request<any, CrawlerConfVO[]>({ url: `${CRAWLER_BASE_URL}`, method: "get", params });
  },
  getFormData(id: string) {
    return request<any, CrawlerConfForm>({ url: `${CRAWLER_BASE_URL}/${id}/form`, method: "get" });
  },
  create(data: CrawlerConfForm) {
    return request({ url: `${CRAWLER_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: CrawlerConfForm) {
    return request({ url: `${CRAWLER_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${CRAWLER_BASE_URL}/${ids}`, method: "delete" });
  },
};
