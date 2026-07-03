/**
 * 数据采集服务节点 API（CrawlerConf）。
 */
import request from "@/utils/request";

/** 爬虫配置 VO。 */
export interface CrawlerConfVO {
  id?: string;
  server_name?: string;
  node?: string;
  ip?: string;
  status?: number;
  order_num?: number;
}

/** 爬虫配置表单。 */
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
  /**
   * 获取爬虫配置列表。
   *
   * @param params - 查询参数。
   * @returns 配置列表。
   */
  getList(params: Record<string, unknown>) {
    return request<any, CrawlerConfVO[]>({ url: `${CRAWLER_BASE_URL}`, method: "get", params });
  },
  /**
   * 获取配置编辑表单。
   *
   * @param id - 配置ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, CrawlerConfForm>({ url: `${CRAWLER_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 创建配置。
   *
   * @param data - 表单数据。
   */
  create(data: CrawlerConfForm) {
    return request({ url: `${CRAWLER_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新配置。
   *
   * @param id - 配置ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: CrawlerConfForm) {
    return request({ url: `${CRAWLER_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 批量删除配置。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${CRAWLER_BASE_URL}/${ids}`, method: "delete" });
  },
};
